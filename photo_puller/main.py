import json
import os
import random
import re
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

# Paths can be overridden with env vars (handy for testing off-HA)
DATA_DIR = Path(os.environ.get("PP_DATA_DIR", "/data"))
OPTIONS_FILE = DATA_DIR / "options.json"
COLLECTIONS_FILE = DATA_DIR / "collections.json"
PHOTO_DIR = Path(os.environ.get("PP_PHOTO_DIR", "/share/photo_puller"))
UI_FILE = Path(os.environ.get("PP_UI_FILE", "/ui.html"))
PORT = int(os.environ.get("PP_PORT", "8099"))
MANIFEST = PHOTO_DIR / "collections.json"

EVENT_PHOTO = "photo_puller_updated"
EVENT_COLLECTIONS = "photo_puller_collections_changed"
S6_ENV_DIRS = ("/run/s6/container_environment", "/var/run/s6/container_environment")


def get_supervisor_token():
    """The base image's s6-overlay strips env vars from our process, so if the token isn't
    in the environment, read it from where s6 stashes the container environment."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if token:
        return token
    for d in S6_ENV_DIRS:
        try:
            return (Path(d) / "SUPERVISOR_TOKEN").read_text().strip()
        except OSError:
            pass
    return None


SUPERVISOR_TOKEN = get_supervisor_token()
UNSPLASH_API = "https://api.unsplash.com"
INGRESS_IPS = {"172.30.32.2", "127.0.0.1"}  # only the HA ingress gateway may talk to us
ORIENTATIONS = ("landscape", "portrait", "both")

DEFAULT_COLLECTIONS = [
    {
        "name": "City",
        "search_terms": ["city skyline night", "european city", "historic city"],
        "orientation": "landscape",
    },
    {
        "name": "Ocean",
        "search_terms": ["ocean waves", "beach sunset", "coastline"],
        "orientation": "both",
    },
]


def log(msg):
    print(msg, flush=True)


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------- settings + collections ----------

def load_options():
    try:
        return json.loads(OPTIONS_FILE.read_text())
    except Exception:
        return {}


def load_collections():
    try:
        return json.loads(COLLECTIONS_FILE.read_text())
    except (FileNotFoundError, ValueError):
        save_collections(DEFAULT_COLLECTIONS)
        return json.loads(json.dumps(DEFAULT_COLLECTIONS))


def save_collections(collections):
    COLLECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = COLLECTIONS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(collections, indent=2))
    os.replace(tmp, COLLECTIONS_FILE)


def validate_collections(raw):
    """Return (clean_list, error_message)."""
    if not isinstance(raw, list):
        return None, "Bad data"
    if len(raw) > 30:
        return None, "That's a lot of collections. 30 max."
    clean, seen = [], set()
    for c in raw:
        if not isinstance(c, dict):
            return None, "Bad data"
        name = str(c.get("name", "")).strip()[:40]
        slug = slugify(name)
        if not slug:
            return None, "Every collection needs a name (letters or numbers)."
        if slug in seen:
            return None, f"Two collections turn into the same ID '{slug}'. Rename one."
        seen.add(slug)
        terms = [str(t).strip()[:80] for t in c.get("search_terms", []) if str(t).strip()][:20]
        if not terms:
            return None, f"'{name}' needs at least one search term."
        orientation = c.get("orientation")
        if orientation not in ORIENTATIONS:
            return None, f"'{name}' needs an orientation."
        clean.append({"name": name, "search_terms": terms, "orientation": orientation})
    return clean, None


def build_jobs(collections):
    """One job per collection + orientation. 'both' becomes two jobs."""
    jobs = []
    for c in collections:
        slug = slugify(c["name"])
        orients = ["landscape", "portrait"] if c["orientation"] == "both" else [c["orientation"]]
        for o in orients:
            jobs.append(
                {"key": f"{slug}_{o}", "slug": slug, "name": c["name"],
                 "orientation": o, "terms": c["search_terms"]}
            )
    return jobs


def write_manifest(jobs):
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    data = [{"slug": j["slug"], "name": j["name"], "orientation": j["orientation"]} for j in jobs]
    MANIFEST.write_text(json.dumps(data))


# ---------- talking to Home Assistant ----------

def fire_event(event_type, data):
    if not SUPERVISOR_TOKEN:
        log("No SUPERVISOR_TOKEN, can't notify Home Assistant")
        return
    try:
        r = requests.post(
            f"http://supervisor/core/api/events/{event_type}",
            headers={"Authorization": f"Bearer {SUPERVISOR_TOKEN}"},
            json=data,
            timeout=10,
        )
        if r.status_code != 200:
            log(f"Event {event_type} failed: {r.status_code} {r.text}")
    except Exception as e:
        log(f"Event {event_type} error: {e}")


def fire_async(event_type, data):
    threading.Thread(target=fire_event, args=(event_type, data), daemon=True).start()


# ---------- fetching photos ----------

def fetch_photo(job, key, size):
    """Returns None on success or an error message."""
    headers = {"Authorization": f"Client-ID {key}"}
    term = random.choice(job["terms"])
    label = job["key"]
    log(f"[{label}] fetching: {term}")

    resp = requests.get(
        f"{UNSPLASH_API}/photos/random",
        headers=headers,
        params={"query": term, "orientation": job["orientation"]},
        timeout=15,
    )
    if resp.status_code == 401:
        return "Unsplash says the Access Key is bad (401). Check the add-on Configuration tab."
    if resp.status_code == 403:
        return "Unsplash rate limit hit (403). Raise the interval or cut collections."
    if resp.status_code != 200:
        return f"Unsplash error {resp.status_code}"

    data = resp.json()
    img = requests.get(data["urls"][size], timeout=60)
    if img.status_code != 200:
        return f"Download failed ({img.status_code})"

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    final = PHOTO_DIR / f"{label}.jpg"
    tmp = PHOTO_DIR / f".{label}.tmp"
    tmp.write_bytes(img.content)
    os.replace(tmp, final)  # atomic, HA never reads a half-written file

    meta = {
        "slug": job["slug"],
        "name": job["name"],
        "orientation": job["orientation"],
        "search_term": term,
        "photographer": data.get("user", {}).get("name"),
        "photo_url": data.get("links", {}).get("html"),
        "fetched_at": now_iso(),
    }
    (PHOTO_DIR / f"{label}.json").write_text(json.dumps(meta))

    try:  # Unsplash API rules ask for this ping when a photo is used
        requests.get(data["links"]["download_location"], headers=headers, timeout=10)
    except Exception:
        pass

    log(f"[{label}] saved ({len(img.content) // 1024} KB)")
    fire_event(EVENT_PHOTO, meta)
    return None


class Worker:
    def __init__(self):
        self.wake = threading.Event()
        self.lock = threading.Lock()
        self.pending = set()
        self.errors = {}
        self.busy = False
        self.next_full = time.time()

    def request(self, keys):
        with self.lock:
            self.pending.update(keys)
        self.wake.set()

    def run(self):
        time.sleep(10)
        write_manifest(build_jobs(load_collections()))
        fire_event(EVENT_COLLECTIONS, {})
        while True:
            self.wake.wait(timeout=max(0, self.next_full - time.time()))
            self.wake.clear()
            with self.lock:
                pending, self.pending = set(self.pending), set()
            opts = load_options()
            full = time.time() >= self.next_full
            if full:
                self.next_full = time.time() + max(5, int(opts.get("interval_minutes", 60))) * 60
            jobs = build_jobs(load_collections())
            todo = [j for j in jobs if full or j["key"] in pending]
            if not todo:
                continue
            key = opts.get("unsplash_access_key")
            self.busy = True
            try:
                for j in todo:
                    if not key:
                        self.errors[j["key"]] = "No Unsplash Access Key set (add-on Configuration tab)."
                        continue
                    try:
                        err = fetch_photo(j, key, opts.get("image_size", "regular"))
                    except Exception as e:
                        log(traceback.format_exc())
                        err = f"Error: {e}"
                    if err:
                        log(f"[{j['key']}] {err}")
                        self.errors[j["key"]] = err
                    else:
                        self.errors.pop(j["key"], None)
                    time.sleep(2)
            finally:
                self.busy = False


worker = Worker()


# ---------- web UI ----------

def build_state():
    opts = load_options()
    collections = load_collections()
    images = {}
    for j in build_jobs(collections):
        k = j["key"]
        meta = {}
        has = (PHOTO_DIR / f"{k}.jpg").exists()
        if has:
            try:
                meta = json.loads((PHOTO_DIR / f"{k}.json").read_text())
            except Exception:
                pass
        images[k] = {"has_image": has, "meta": meta, "error": worker.errors.get(k)}
    return {
        "collections": collections,
        "options": {
            "has_key": bool(opts.get("unsplash_access_key")),
            "interval_minutes": int(opts.get("interval_minutes", 60)),
            "image_size": opts.get("image_size", "regular"),
        },
        "images": images,
        "busy": worker.busy,
        "next_cycle": datetime.fromtimestamp(worker.next_full, timezone.utc).isoformat(),
    }


IMAGE_RE = re.compile(r"^[a-z0-9_]+_(landscape|portrait)\.jpg$")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json", cache=False):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if not cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _allowed(self):
        if self.client_address[0] not in INGRESS_IPS:
            self._send(403, {"error": "forbidden"})
            return False
        return True

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 65536:
            return None
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return None

    def do_GET(self):
        if not self._allowed():
            return
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, UI_FILE.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/state":
            self._send(200, build_state())
        elif path.startswith("/image/"):
            name = path[len("/image/"):]
            f = PHOTO_DIR / name
            if IMAGE_RE.match(name) and f.is_file():
                self._send(200, f.read_bytes(), "image/jpeg")
            else:
                self._send(404, {"error": "not found"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._allowed():
            return
        path = self.path.split("?")[0]
        body = self._body()
        if body is None:
            return self._send(400, {"error": "Bad request"})

        if path == "/api/collections":
            clean, err = validate_collections(body.get("collections"))
            if err:
                return self._send(400, {"error": err})
            old = {slugify(c["name"]): c for c in load_collections()}
            save_collections(clean)
            jobs = build_jobs(clean)
            write_manifest(jobs)
            fire_async(EVENT_COLLECTIONS, {})
            # fetch right away for anything new, or whose terms/orientation changed
            to_fetch = []
            for j in jobs:
                prev = old.get(j["slug"])
                changed = prev is None or prev["search_terms"] != j["terms"]
                if changed or not (PHOTO_DIR / f"{j['key']}.jpg").exists():
                    to_fetch.append(j["key"])
            worker.request(to_fetch)
            return self._send(200, {"ok": True, "fetching": len(to_fetch)})

        if path == "/api/fetch":
            slug = body.get("slug")
            keys = [j["key"] for j in build_jobs(load_collections()) if not slug or j["slug"] == slug]
            worker.request(keys)
            return self._send(200, {"ok": True, "fetching": len(keys)})

        self._send(404, {"error": "not found"})


def main():
    load_collections()  # creates the defaults on first run
    threading.Thread(target=worker.run, daemon=True).start()
    log("Home Assistant link: " + ("OK" if SUPERVISOR_TOKEN else "NO TOKEN, entities won't update live"))
    log(f"Photo Puller UI listening on port {PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
