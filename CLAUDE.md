# CLAUDE.md — The Shining Prince Meets The Knight Errant

## Project overview

Static GitHub Pages web app displaying ~1,021 literary mashup sentences combining The Tale of Genji (first half) and Don Quixote (second half), in the exquisite-corpse tradition. See the full technical plan at `/Users/Mark/.claude/plans/ok-here-is-a-unified-pearl.md`.

## Coding standards

- **Every function must have a docstring** explaining what it does, its parameters, and its return value. This is a hard requirement for this project.
- **Inline comments** should explain non-obvious logic (e.g. why a particular split priority, why a threshold value was chosen).
- **Word boundaries must always be respected** when splitting strings. Never split mid-word. All sentence halving operates on whitespace-tokenised word lists and reassembles with spaces.
- No separator is inserted between the Genji and Quixote halves in the `display` field — the halves are joined directly. Colour coding in the UI provides the visual distinction.

## Project structure

```
pipeline/          Python scripts (run offline to generate sentences.json)
config/            JSON configuration files (scoring weights, character ranks, ignore patterns)
web/               Frontend (vanilla JS, no framework)
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
# Then open http://localhost:8000/web/
```

## Important constraints

- **Character ranks review checkpoint**: `config/character_ranks.json` must be reviewed and approved by the user before `character_detector.py` or any downstream code that reads it is written. See plan Phase A step 4 checkpoint.
- **Frontend design deferred**: Full HTML structure, styling, and audio integration wait for a design prototype. Phase B builds JS logic modules only (queue.js, player.js, keyboard.js) and a minimal stub index.html.
- **No mid-word splits**: The sentence halver tokenises by whitespace and splits between tokens only.
- **Source materials are read-only**: Never modify files under `source-materials/`.

## Architecture summary

The system is split into two independent phases:

1. **Pipeline** (Python, offline): Parses source texts → extracts and cleans sentences → halves each sentence at a clause boundary → scores sentences and pairs → writes `sentences.json`. All pipeline logic is in pure functions (except `text_loader.py` which handles I/O) to make unit testing straightforward.

2. **Frontend** (vanilla JS): Loads `sentences.json` on page load → uses a Fisher-Yates depletion queue to select pairs without repeating within a window of 30 → displays one pair at a time with auto-play, navigation, and source-sentence reveal on hover.
