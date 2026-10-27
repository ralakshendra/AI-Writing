# AI Writing

A standalone, GitHub-ready digital writing library built from the supplied AI Community Writing archive. It is intentionally independent from the cohort website and uses a neutral AI Writing identity.

## What is included

- 511 archived lesson pages plus 29 downloadable resources, including 170 newly added course pages.
- Exact folder and subfolder navigation with breadcrumbs, global search, saved resources, and local progress tracking.
- Readable lesson content in a spacious, full-page view that opens in a new tab.
- Entire resource tiles are clickable, with a prominent open-resource action.
- Lesson images extracted from the archived snapshots and stored locally.
- YouTube and Loom lesson links with preserved thumbnails when available.
- Responsive layouts for phone, tablet, and desktop.

## Work locally

Run `npm run preview`, then open `http://127.0.0.1:8777/`.

Run `npm run check` to verify the catalogue, media files, required interface elements, and removal of previous branding. Run `npm run build` to create the deployable `dist` folder.

## Refresh the archive

The original ZIP predates the October 27 Drive additions. Preserve the current catalog and merge its Drive-backed records and attachment mapping when refreshing; importing only that ZIP replaces the catalog with the older source set. See `docs/DRIVE_UPDATE_2026-10-27.md` and `docs/drive-resource-map.json`.

Run `npm run archive:import`. The importer treats archived pages as source material, preserves readable lesson content and snapshot media, and removes scripts, account controls, and unrelated page chrome.

## GitHub Pages

The included workflow builds and publishes `dist` whenever `main` is pushed. In the repository settings, set Pages to use **GitHub Actions** as its source.
