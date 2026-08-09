# Vynex

Smart Semantic Web TV Platform demo for CENG384 Project III.

## Run

Open `index.html` directly in a browser.

For a local server:

```bash
python -m http.server 5500
```

Then visit `http://localhost:5500`.

## Included Modules

- Hash-based frontend routes: `/login`, `/register`, `/`, `/live-tv`, `/movies`, `/series`, `/discover`, `/content/:id`, `/my-list`, `/profile`
- Mock authentication with protected routes and logout
- Reusable layout, sidebar, topbar, content cards, hero, filters, video player, channel list, and EPG guide
- Mock data and API service abstraction under `data/` and `services/`
- Netflix-style home screen and Plex-style Live TV screen
- Semantic discovery UI prepared for a future AI/search backend
- PWA manifest and service worker
- PWA manifest and service worker
