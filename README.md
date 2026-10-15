# AI Writing

A standalone, GitHub-ready digital writing library built from the supplied AI Community Writing archive. It is intentionally independent from the cohort website and uses a neutral AI Writing identity.

## What is included

- All 335 archived resources, organized by their original top-level folders.
- Search, topic/folder/format filters, saved resources, and local progress tracking.
- Readable lesson content inside the site.
- Lesson images extracted from the archived snapshots and stored locally.
- YouTube and Loom lesson links with preserved thumbnails when available.
- Responsive layouts for phone, tablet, and desktop.

## Work locally

Run `npm run preview`, then open `http://127.0.0.1:8777/`.

Run `npm run check` to verify the catalogue, media files, required interface elements, and removal of previous branding. Run `npm run build` to create the deployable `dist` folder.

## Refresh the archive

Run `npm run archive:import`. The importer treats archived pages as source material, preserves readable lesson content and snapshot media, and removes scripts, account controls, and unrelated page chrome.

## GitHub Pages

The included workflow builds and publishes `dist` whenever `main` is pushed. In the repository settings, set Pages to use **GitHub Actions** as its source.
