# The Shining Prince Meets The Knight Errant

A literary mashup web app combining *The Tale of Genji* and *Don Quixote* in the exquisite-corpse tradition. Each pair joins the first half of a sentence from Genji with the second half of a sentence from Quixote — exploiting the tonal contrast between Genji's interior, melancholy register and Quixote's comic, earthy one.

Around 1,021 pairs, generated offline from the Project Gutenberg texts and served as a static site on GitHub Pages.

---

## Using the site

- **← →** or the Prev / Next buttons to navigate
- **Space** or the Play button to enter auto-play mode — pairs advance automatically, each word revealed one by one
- Click a chapter reference (e.g. *Genji Vol. 3 · Ch. X*) to reveal the original source sentence
- **♪ muted** in the top bar to start the background music playlist
- **i** or the About button for background and keyboard shortcuts
- Share button copies a direct link to the current pair (`#gq-NNNN`)

---

## Project structure

```
pipeline/          Offline Python scripts that generate pairs.json from source texts
config/            Scoring weights, character registry, ignore patterns
web/               Static frontend (React 18, no build step)
  index.html       App shell
  app.jsx          Complete React app
  data/pairs.json  The pair dataset (currently dev sample; replace with full output)
  audio/           Self-hosted MP3s + manifest.json
source-materials/  Source texts and character lists (read-only)
dev_sample.json    50-pair development sample
sentences.json     Full 1,021-pair production dataset (generated, committed to repo)
```

---

## Running locally

```bash
python3 -m http.server 8000
# Open http://localhost:8000/web/
```

No build step. The frontend loads React and Babel from CDN and transpiles `app.jsx` in-browser.

---

## Pipeline — generating pairs

The Python pipeline reads the source texts, cleans and segments them into sentences, halves each sentence at a clause boundary, scores sentence halves, and pairs the top-scoring Genji halves with top-scoring Quixote halves.

### Setup (one-time)

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

### Commands

```bash
# Run unit tests
cd pipeline && python -m pytest tests/ -v

# Generate a 50-pair development sample
python pipeline/generate_pairs.py --count 50 --output dev_sample.json

# Generate the full production set
python pipeline/generate_pairs.py --count 1021 --output sentences.json
```

After generating the full set, copy it into the frontend:

```bash
cp sentences.json web/data/pairs.json
```

### Configuration

| File | Purpose |
|---|---|
| `config/character_ranks.json` | Character registry: canonical names, variants, major/minor rank, score weights |
| `config/scoring_weights.json` | Numeric knobs for sentence and pair scoring |
| `config/ignore_patterns.json` | Regex patterns to exclude lines and sentences during cleaning |

---

## Audio

Drop MP3 files into `web/audio/` and list them in `web/audio/manifest.json`. The app shuffles the playlist on load and streams tracks progressively. See `web/audio/README.md` for details.

---

## Deployment

See `web/DEPLOY.md` for the GitHub Pages deployment checklist.

---

## Source texts

Both texts are in the public domain via Project Gutenberg:

- *The Tale of Genji* — Murasaki Shikibu, tr. Suematsu Kenchio
- *Don Quixote* — Miguel de Cervantes, tr. John Ormsby
