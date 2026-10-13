# Changelog

## 1.2.1

### Fixed
- The add-on couldn't tell Home Assistant when a new photo landed ("No SUPERVISOR_TOKEN" in
  the log), so image entities didn't refresh on their own and new collections didn't get
  entities until you reloaded the integration. The add-on now finds its token and notifies
  Home Assistant properly.
- The add-on log now says at startup whether its link to Home Assistant is working.

## 1.2.0

### Changed
- **Breaking:** collections are no longer set on the Configuration tab. They now live in a
  new web UI (the **Photo Puller** panel in the sidebar, or **Open Web UI** on the add-on page).
  The Configuration tab keeps only your Unsplash Access Key, the interval, and the image size.
- The first time you start this version, you get two example collections (City and Ocean).
  Edit or delete them, and re-create any custom collections you had before.

### Added
- Web UI for managing collections: add, edit, and delete collections, one search term per
  line, and choose Landscape, Portrait, or Both for each.
- Photo previews with the photographer's name on each collection card.
- **Fetch now** per collection and **Fetch all now**.
- Saving collections pulls photos right away for anything new or whose search terms changed.
- A live estimate of Unsplash requests per hour, with a warning when you're near the
  50 per hour limit.
- Clear error messages on each card (bad key, rate limit, and so on).
- Add-on documentation (`DOCS.md`).

## 1.1.1

### Fixed
- The add-on failed to build on newer Supervisor versions with the error
  "base name ($BUILD_FROM) should not be blank". The Dockerfile now sets a default base image.

### Added
- Add-on icon and logo, and icons and logos for the integration.

## 1.1.0

### Added
- Multiple collections (for example City and Ocean), each with its own search terms.
- Per-collection choice of Landscape, Portrait, or Both.
- The integration now creates one device per collection, with an image entity for each
  orientation, and adds new entities on its own when collections change.
- Image entities carry `photographer`, `photo_url`, and `search_term` attributes.

### Changed
- Default image size is now `regular` instead of `full`, so images are smaller and quicker to load.

## 1.0.0

### Added
- Initial release. Pulls random Unsplash photos on a schedule, saves them to
  `/share`, and tells Home Assistant when a new photo is ready so the image
  entities update right away.
- Configurable Unsplash Access Key, search terms, interval, and image size.
