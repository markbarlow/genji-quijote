# Audio

Drop your `.mp3` files into this folder and list them in `manifest.json`.

The app:
- Fetches `manifest.json` on load
- Fisher-Yates shuffles the `tracks` array
- Plays the first one when you click `♪ muted`
- On track end, advances to the next; reshuffles when it wraps
- Streams progressively via the `<audio>` element — no need to wait for full download

GitHub Pages serves MP3s with range requests, so progressive streaming and seeking both work fine.

Notes:
- Filenames with spaces are fine but URL-encode them in the manifest if needed (`My%20Track.mp3`)
- Keep individual files reasonable (a few MB each) — many small files beat one big one for first-play latency
- 1GB GitHub Pages soft cap; 100GB/month bandwidth — plenty for personal use
