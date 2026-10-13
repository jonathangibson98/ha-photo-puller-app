# Photo Puller

Pulls random photos from [Unsplash](https://unsplash.com) on a schedule and saves them
for Home Assistant. You choose what to pull (city, ocean, forest, whatever) in a web UI,
and the companion **Photo Puller integration** turns the photos into image entities that
update the moment a new photo lands. Use them as dashboard wallpapers, picture cards,
or anywhere an image entity works.

## What you need

- Home Assistant OS or Supervised (add-ons aren't available on Container installs)
- A free Unsplash API key (see below)
- The **Photo Puller integration** from the same repository. The add-on downloads the
  photos, and the integration is what creates the image entities in Home Assistant.

## Setup

### 1. Get an Unsplash Access Key

1. Go to <https://unsplash.com/developers> and sign in or create a free account.
2. Click **Your apps** > **New Application**, accept the terms, and give it a name.
3. Copy the **Access Key**. This is the one you want, not the Secret Key.

A new app starts in "Demo" mode, which allows 50 requests per hour. That's plenty for this add-on.

### 2. Configure the add-on

Open the **Configuration** tab, fill in the options below, and click **Save**.

| Option | What it does |
| --- | --- |
| `unsplash_access_key` | Your Unsplash Access Key. |
| `interval_minutes` | How often to pull fresh photos. 5 to 1440, default 60. |
| `image_size` | `small` (about 400px wide), `regular` (about 1080px, the default), or `full` (original size, can be 10 MB or more). |

Start the add-on. If you change the key or any option later, restart the add-on to be safe.

### 3. Choose what to pull (the web UI)

Open **Photo Puller** from the sidebar, or click **Open Web UI** on the add-on page.
You'll see one card per collection. The add-on starts with two examples, City and Ocean.
Edit or delete them as you like.

Each collection has:

- **Name.** Becomes part of the entity ID (see below). Letters and numbers are best.
- **Search terms.** One per line. Each time a photo is pulled, one term is picked at random.
  Put several related terms in one collection for variety, for example "historic city",
  "european city", and "city skyline night" in a City collection.
- **Save as.** `Landscape`, `Portrait`, or `Both`. Landscape and portrait photos are saved
  and updated separately.

Buttons:

- **Save changes** saves your collections and immediately pulls photos for anything new
  or whose search terms changed.
- **Fetch now** (on a card) pulls a new photo for just that collection.
- **Fetch all now** pulls new photos for everything.
- **Add collection** and the **X** on a card add and delete collections.

The header shows how many Unsplash requests per hour your setup uses and warns you if you're
close to the 50 per hour limit.

### 4. Add the integration

Install the Photo Puller integration (through HACS as a custom repository, or by copying
`custom_components/photo_puller` into your config folder), restart Home Assistant, then go to
**Settings > Devices & services > Add Integration > Photo Puller** and click Submit.
You only do this once. New collections show up on their own after that.

## Entities

Every collection becomes a device, with one image entity per orientation:

```
image.<collection name>_photos_landscape
image.<collection name>_photos_portrait
```

For example, a collection named `Ocean` set to Both gives you
`image.ocean_photos_landscape` and `image.ocean_photos_portrait`. The web UI shows the exact
entity IDs under each collection.

Names are lowercased and anything that isn't a letter or number becomes an underscore,
so "Ocean Views!" becomes `ocean_views`. Two collections can't end up with the same ID.

Each entity has these attributes:

- `photographer`
- `photo_url` (link to the photo on Unsplash)
- `search_term` (the term that found it)

Unsplash asks apps to credit photographers, so consider showing these on your dashboard.

### Use them on a dashboard

Add a Picture card (or Picture Entity card) and pick the image entity, or in YAML:

```yaml
type: picture-entity
entity: image.ocean_photos_landscape
show_state: false
show_name: false
```

## Events

Each time a photo is saved, the add-on fires `photo_puller_updated` on the Home Assistant
event bus with `slug`, `name`, `orientation`, `search_term`, `photographer`, `photo_url`,
and `fetched_at`. You can use it as an automation trigger.

The add-on also fires `photo_puller_collections_changed` when it starts or when you save
collections. The integration listens for it to add new entities.

## Where the files live

Photos are saved in Home Assistant's `/share/photo_puller/` folder as
`<collection>_<orientation>.jpg`, with a small `.json` file next to each one holding the
photographer info. Each new photo overwrites the previous one, so storage stays small.
Your collections are stored in the add-on's own data, so they survive restarts and updates.

## Troubleshooting

**The web UI says "No Unsplash Access Key yet."**
Add your key on the Configuration tab, Save, and restart the add-on.

**A card shows "Unsplash says the Access Key is bad (401)."**
The key is wrong. Make sure you copied the Access Key, not the Secret Key, with no extra spaces.

**A card shows "Unsplash rate limit hit (403)."**
You used up the 50 requests per hour. Each image costs one request per cycle. Raise
`interval_minutes` or remove collections or orientations you don't need.

**The add-on is running but I have no image entities.**
Install and add the Photo Puller integration (step 4). If it's already added, reload it from
Settings > Devices & services > Photo Puller.

**An entity shows "unavailable" or has no picture yet.**
It's waiting for its first photo. Click **Fetch now** on that collection and check the add-on
Log tab for errors.

**I deleted a collection but its entities are still there.**
Home Assistant keeps them as "unavailable." Remove them in Settings > Entities.

**The add-on won't install or build.**
Check the Supervisor log (Settings > System > Logs, then pick Supervisor) and the add-on's own
Log tab, and include them if you open an issue.

## Credits

Photos come from [Unsplash](https://unsplash.com) and belong to their photographers.
This add-on is not affiliated with or endorsed by Unsplash.
