# CLAUDE.md — The Shining Prince Meets The Knight Errant

## Project overview

Static GitHub Pages web app displaying ~1,021 literary mashup sentences combining The Tale of Genji (first half) and Don Quixote (second half), in the exquisite-corpse tradition. See the full technical plan at `/Users/Mark/.claude/plans/ok-here-is-a-unified-pearl.md`.

## Coding standards

- **Every function must have a docstring** explaining what it does, its parameters, and its return value. This is a hard requirement for this project.
- **Inline comments** should explain non-obvious logic (e.g. why a particular split priority, why a threshold value was chosen).
- **Word boundaries must always be respected** when splitting strings. Never split mid-word. All sentence halving operates on whitespace-tokenised word lists and reassembles with spaces.
- The Genji and Quijote halves in the `display` field are joined with a single space. Colour coding in the UI provides the visual distinction between them.

## Project structure

```
pipeline/          Python scripts (run offline to generate sentences.json)
config/            JSON configuration files (scoring weights, character ranks, ignore patterns)
docs/              Frontend (React 18 via CDN + Babel standalone, no build step)
  index.html       App shell — loads React, Babel, fonts, boots app.jsx
  app.jsx          Complete React app (all UI logic, queue, player, keyboard)
  favicon.svg      Two-circle favicon in project colours
  og-image.png     1200×630 social preview card
  audio/           Self-hosted MP3s + manifest.json playlist
  data/            pairs.json — production dataset (1,021 pairs)
  queue.js         Original Fisher-Yates queue module (superseded by app.jsx, kept for reference)
  player.js        Original auto-play timer module (superseded, kept for reference)
  keyboard.js      Original keyboard bindings module (superseded, kept for reference)
source-materials/  Source texts and character lists — do not modify these files
sentences.json     Generated artifact committed to repo — the production data file
```

## Key commands

```bash
# Install pipeline dependencies (one-time setup)
pip install spacy
python -m spacy download en_core_web_sm

# Run unit tests
cd pipeline && python -m pytest tests/ -v

# Generate a development sample (50 pairs)
python pipeline/generate_pairs.py --count 50 --output dev_sample.json

# Generate the full production set (1,021 pairs)
python pipeline/generate_pairs.py --count 1021 --output sentences.json

# Serve the frontend locally for testing
python -m http.server 8000
# Then open http://localhost:8000/docs/
```

## Important constraints

- **No mid-word splits**: The sentence halver tokenises by whitespace and splits between tokens only.
- **Source materials are read-only**: Never modify files under `source-materials/`.
- **Frontend uses no build step**: `app.jsx` is transpiled in-browser by Babel standalone. Do not introduce a bundler or npm dependencies.

## Architecture summary

The system is split into two independent phases:

1. **Pipeline** (Python, offline): Parses source texts → extracts and cleans sentences → halves each sentence at a clause boundary → scores sentences and pairs → writes `sentences.json`. All pipeline logic is in pure functions (except `text_loader.py` which handles I/O) to make unit testing straightforward.

2. **Frontend** (React 18, no build step): Loads `docs/data/pairs.json` on page load → Fisher-Yates depletion queue (no repeat within window of 30) → displays one pair at a time with auto-play, word-by-word reveal, prev/next navigation, inline source reveal, self-hosted audio playlist, and shareable `#gq-NNNN` URLs. Genji half rendered in moss-green, Quijote half in terracotta. Responsive (desktop-first). To swap in the full dataset, replace `docs/data/pairs.json` with the output of `generate_pairs.py`.
