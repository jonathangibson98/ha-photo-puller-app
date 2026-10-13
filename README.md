# Photo Puller for Home Assistant

Pulls random Unsplash photos for collections you define (city, ocean, whatever)
and gives you Home Assistant image entities that update the moment a new photo lands.

This repo has two parts. You need both:

1. **Add-on** (`photo_puller/`): holds your Unsplash key and settings, downloads the photos.
2. **Integration** (`custom_components/photo_puller/`): creates the image entities.

Requires Home Assistant OS or Supervised (add-ons don't exist on Container installs).
Get a free Unsplash Access Key at https://unsplash.com/developers.

## Install the add-on

1. Settings > Add-ons > Add-on Store > three dots (top right) > Repositories
2. Paste `https://github.com/jonathangibson98/ha-photo-puller` and click Add
3. Refresh the page, scroll down, open **Photo Puller**, and Install
4. Configuration tab: paste your Unsplash Access Key, pick an interval and image size, Save
5. Start, then open **Photo Puller** from the sidebar (or the add-on's Open Web UI button) to set up what to pull

## Install the integration (HACS)

1. HACS > three dots (top right) > Custom repositories
2. Paste `https://github.com/jonathangibson98/ha-photo-puller`, set Type to **Integration**, Add
3. Find **Photo Puller** in HACS, Download, then restart Home Assistant
4. Settings > Devices & services > Add Integration > **Photo Puller** > Submit

No HACS? Copy `custom_components/photo_puller` into `/config/custom_components/` and restart.

## Collections (managed in the web UI)

Open the **Photo Puller** panel and add as many collections as you like. Each one has a name,
search terms (one per line, a random one is picked each pull), and a choice of
Landscape, Portrait, or Both. Hit Save and new photos get pulled right away.

Every collection becomes a device with one image entity per orientation, e.g.
`image.ocean_photos_landscape`. Each image entity carries `photographer`, `photo_url`
and `search_term` attributes. Unsplash asks that you credit photographers.

Unsplash's free tier allows 50 requests per hour. Each image costs one request per cycle.
