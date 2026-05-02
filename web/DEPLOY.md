# Deploy checklist

Quick guide for getting this onto GitHub Pages.

## 1. Push to GitHub

Push the project to a repo. The static-site root is the project root — no
build step.

## 2. Enable Pages

In your repo's **Settings → Pages**:
- **Source:** Deploy from a branch
- **Branch:** `main` (or whichever holds the latest)
- **Folder:** `/ (root)`

GitHub will give you a URL like `https://YOURNAME.github.io/REPO-NAME/`.

## 3. Things to update once you know the URL

### A. Open Graph + Twitter card image URLs

Some chat apps (notably iMessage) won't resolve relative OG image paths.
In `index.html`, swap these two lines:

```html
<meta property="og:image" content="og-image.png" />
<meta name="twitter:image" content="og-image.png" />
```

…to absolute URLs:

```html
<meta property="og:image" content="https://YOURNAME.github.io/REPO-NAME/og-image.png" />
<meta name="twitter:image" content="https://YOURNAME.github.io/REPO-NAME/og-image.png" />
```

### B. Test the social preview

After the URL is live, paste it into:
- https://www.opengraph.xyz/  (general OG preview)
- https://cards-dev.twitter.com/validator (Twitter card)
…to confirm the preview image and title render.

## 4. Other things still on your TODO

These are independent of deploy but worth doing before sharing widely:

- **About modal links** — `app.jsx` has four `href="#"` placeholder links in
  the About overlay ("Lexicorium" etc). Replace with real URLs (or remove).
- **Audio** — drop your `.mp3` files into `audio/` and list them in
  `audio/manifest.json`. Without files, the audio toggle will be a no-op.
- **Full pair set** — currently uses `data/pairs.json` (the 50-pair dev sample).
  Replace `web/data/pairs.json` with your full `sentences.json` when ready.

## 5. The `.nojekyll` file

A zero-byte `.nojekyll` is included at the project root. It tells GitHub
Pages to skip Jekyll processing — which would otherwise strip files
beginning with `_` or `.`. Belt-and-braces; nothing in this project
currently triggers Jekyll, but it's good insurance.
