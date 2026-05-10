// Main app for "The Shining Prince Meets The Knight Errant"
// state (pair navigation, play/pause, source reveal, about overlay).

const { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } = React;

// ---------------------------------------------------------------------------
// Defaults — exposed as constants in case you want to tune them.
// ---------------------------------------------------------------------------
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "wpm": 150,        // reading speed used to compute auto-play duration; see computeDuration below
  "typingReveal": true,
  "showTimer": true
}/*EDITMODE-END*/;

// ---------------------------------------------------------------------------
// Palette — dark mode, warm-neutral base.
// Genji: muted greens / dusty rose / parchment. Quijote: terracotta / ochre / oxblood.
// ---------------------------------------------------------------------------
const PALETTE = {
  bg: "#13140f",
  bgAlt: "#1a1b15",
  ink: "#e8e2d1",
  inkDim: "#8a857a",
  inkFaint: "#4a4840",
  genji: "#b8c4a0",     // soft moss
  genjiDeep: "#7a8a6a",
  genjiAccent: "#d8b8b0", // dusty rose — chapter ref hover
  quijote: "#d89060",   // terracotta
  quijoteDeep: "#b8583a",
  quijoteAccent: "#e8c890", // ochre — chapter ref hover
  line: "#2a2a22",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function splitWords(text) {
  // Preserve whitespace by splitting on word boundaries — each chunk is either a word or whitespace.
  return text.match(/\S+|\s+/g) || [];
}

// Track whether the viewport is in mobile range (≤600px wide). Components
// read this to swap in tighter spacing/typography without affecting desktop.
function useIsMobile(breakpoint = 600) {
  const [isMobile, setIsMobile] = useState(
    typeof window !== "undefined" ? window.innerWidth <= breakpoint : false
  );
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= breakpoint);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [breakpoint]);
  return isMobile;
}

function formatChapter(ch) {
  // "VOLUME 3 CHAPTER X" -> "Vol. 3 · Ch. X"
  if (!ch) return "";
  const m = ch.match(/VOLUME\s+(\S+)\s+CHAPTER\s+(\S+)/i);
  if (!m) return ch;
  const vol = m[1];
  const chap = m[2].replace(/\.$/, "");
  return `Vol. ${vol} · Ch. ${chap}`;
}

// ---------------------------------------------------------------------------
// Depletion queue (no repeats within window). Ported from codebase.
// ---------------------------------------------------------------------------
function createQueue(pairs, windowSize = 30) {
  let remaining = [];
  let recentIds = [];
  const history = [];
  let historyIndex = -1;

  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function refill() {
    const recentSet = new Set(recentIds);
    let candidates = pairs.filter((p) => !recentSet.has(p.id));
    if (candidates.length === 0) {
      recentIds = [];
      candidates = pairs.slice();
    }
    remaining = shuffle(candidates);
  }

  return {
    next() {
      if (historyIndex < history.length - 1) {
        historyIndex++;
        return history[historyIndex];
      }
      if (remaining.length === 0) refill();
      const pair = remaining.pop();
      recentIds.push(pair.id);
      if (recentIds.length > windowSize) recentIds.shift();
      history.push(pair);
      historyIndex = history.length - 1;
      return pair;
    },
    prev() {
      if (historyIndex > 0) {
        historyIndex--;
        return history[historyIndex];
      }
      return null;
    },
    current() {
      return history[historyIndex] || null;
    },
    hasPrev() {
      return historyIndex > 0;
    },
    jumpToId(id) {
      const pair = pairs.find((p) => p.id === id);
      if (!pair) return null;
      // If already in history, reuse
      const idx = history.findIndex((p) => p.id === id);
      if (idx >= 0) {
        historyIndex = idx;
        return pair;
      }
      history.push(pair);
      historyIndex = history.length - 1;
      recentIds.push(pair.id);
      if (recentIds.length > windowSize) recentIds.shift();
      return pair;
    },
    position() {
      return { index: historyIndex + 1, total: pairs.length };
    },
  };
}

// ---------------------------------------------------------------------------
// Typography sets
// ---------------------------------------------------------------------------
const TYPOGRAPHY = {
  cormorant: {
    display: "'Cormorant Garamond', 'EB Garamond', Georgia, serif",
    mono: "'JetBrains Mono', ui-monospace, monospace",
    displayWeight: 400,
  },
};

// ===========================================================================
// App
// ===========================================================================
function App({ tweakValues, pairs }) {
  const { wpm, typingReveal, showTimer } = tweakValues;
  const isMobile = useIsMobile();

  const queueRef = useRef(null);
  if (!queueRef.current) queueRef.current = createQueue(pairs, 30);

  const [pair, setPair] = useState(() => {
    // Respect #gq-NNNN in URL on load
    const hash = window.location.hash.replace("#", "");
    if (hash) {
      const p = queueRef.current.jumpToId(hash);
      if (p) return p;
    }
    return queueRef.current.next();
  });

  const [playing, setPlaying] = useState(false);
  const [timerKey, setTimerKey] = useState(0); // bumps to restart CSS animation
  const [duration, setDuration] = useState(4000);
  const playBtnRef = useRef(null);
  const [playBtnRect, setPlayBtnRect] = useState(null);
  // Measure the Play button whenever something might change its position.
  useEffect(() => {
    const measure = () => {
      if (playBtnRef.current) {
        const r = playBtnRef.current.getBoundingClientRect();
        setPlayBtnRect({ left: r.left, width: r.width, bottom: r.bottom });
      }
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [playing]);
  const [sourceOpen, setSourceOpen] = useState(null); // 'genji' | 'quijote' | null
  const [aboutOpen, setAboutOpen] = useState(false);
  const [audioMuted, setAudioMuted] = useState(true);
  const audioElRef = useRef(null);
  const playlistRef = useRef([]);     // shuffled queue of track URLs
  const playlistIdxRef = useRef(0);

  // --- Self-hosted audio playlist -----------------------------------------
  // Loads audio/manifest.json on mount, shuffles the track list, and uses a
  // single <audio> element to stream tracks one after another. On 'ended',
  // advances to the next track in the shuffled list (re-shuffling at end).
  useEffect(() => {
    let cancelled = false;
    fetch("./audio/manifest.json")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        const tracks = (data.tracks || []).slice();
        // Fisher-Yates shuffle for a real random order
        for (let i = tracks.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [tracks[i], tracks[j]] = [tracks[j], tracks[i]];
        }
        playlistRef.current = tracks;
        playlistIdxRef.current = 0;
        if (audioElRef.current && tracks.length > 0) {
          audioElRef.current.src = tracks[0];
        }
      })
      .catch(() => {
        // Manifest missing or malformed — silent fallback; toggle becomes a no-op visual.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const advanceTrack = useCallback(() => {
    const list = playlistRef.current;
    if (list.length === 0) return;
    playlistIdxRef.current = (playlistIdxRef.current + 1) % list.length;
    // When we wrap, reshuffle so the next cycle is a fresh random order
    if (playlistIdxRef.current === 0) {
      for (let i = list.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [list[i], list[j]] = [list[j], list[i]];
      }
    }
    const audio = audioElRef.current;
    if (audio) {
      audio.src = list[playlistIdxRef.current];
      audio.play().catch(() => {});
    }
  }, []);

  const toggleAudio = useCallback(() => {
    const audio = audioElRef.current;
    if (!audio || playlistRef.current.length === 0) {
      setAudioMuted((m) => !m);
      return;
    }
    if (audioMuted) {
      audio.volume = 0.7;
      audio.play().catch(() => {});
      setAudioMuted(false);
    } else {
      audio.pause();
      setAudioMuted(true);
    }
  }, [audioMuted]);
  const [copied, setCopied] = useState(false);
  const [fading, setFading] = useState(false);
  // Manual nav crossfade: 220ms out, swap pair, then re-render at full opacity.
  // Auto-advance during play uses its own word-fade so we don't double-fade.
  const fadeTimerRef = useRef(null);
  const swapWithFade = useCallback((doSwap) => {
    if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current);
    setFading(true);
    fadeTimerRef.current = setTimeout(() => {
      doSwap();
      setFading(false);
    }, 140);
  }, []);

  const timerRef = useRef(null);

  // --- sync URL hash with current pair ------------------------------------
  useEffect(() => {
    if (pair) {
      const newHash = `#${pair.id}`;
      if (window.location.hash !== newHash) {
        history.replaceState(null, "", newHash);
      }
    }
  }, [pair]);

  // --- compute duration from wpm / word count -----------------------------
  // Display time (ms) = (word count / wpm) * 60000, floored at 4 seconds.
  // wpm is set in TWEAK_DEFAULTS above. The 4s floor ensures very short pairs
  // still have enough dwell time to read comfortably.
  const computeDuration = useCallback(
    (p) => {
      const words = p.display.split(/\s+/).filter(Boolean).length;
      return Math.max(4000, (words / wpm) * 60000);
    },
    [wpm]
  );

  // --- play loop ----------------------------------------------------------
  useEffect(() => {
    if (!playing || !pair) return;
    const d = computeDuration(pair);
    setDuration(d);
    setTimerKey((k) => k + 1);
    timerRef.current = setTimeout(() => {
      setPair(queueRef.current.next());
    }, d);
    return () => clearTimeout(timerRef.current);
  }, [playing, pair, computeDuration]);

  // --- controls -----------------------------------------------------------
  const next = useCallback(() => {
    setPlaying(false);
    clearTimeout(timerRef.current);
    setSourceOpen(null);
    swapWithFade(() => setPair(queueRef.current.next()));
  }, [swapWithFade]);

  const prev = useCallback(() => {
    if (!queueRef.current.hasPrev()) return;
    setPlaying(false);
    clearTimeout(timerRef.current);
    setSourceOpen(null);
    swapWithFade(() => setPair(queueRef.current.prev()));
  }, [swapWithFade]);

  const togglePlay = useCallback(() => {
    setPlaying((p) => !p);
  }, []);

  const copyLink = useCallback(() => {
    const url = `${window.location.origin}${window.location.pathname}#${pair.id}`;
    navigator.clipboard?.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }, [pair]);

  // --- keyboard shortcuts -------------------------------------------------
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
      else if (e.key === " ") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === "Escape") {
        setSourceOpen(null);
        setAboutOpen(false);
      } else if (e.key === "i" || e.key === "?") {
        setAboutOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev, togglePlay]);

  const typo = TYPOGRAPHY.cormorant;

  // ---------------------------------------------------------------------
  const commonProps = {
    pair,
    typo,
    playing,
    typingReveal,
    sourceOpen,
    setSourceOpen,
    fading,
    isMobile,
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100%",
        background: PALETTE.bg,
        color: PALETTE.ink,
        fontFamily: typo.display,
        fontWeight: typo.displayWeight,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Top chrome */}
      <TopBar
        mono={typo.mono}
        onAbout={() => setAboutOpen(true)}
        audioMuted={audioMuted}
        onToggleAudio={toggleAudio}
        isMobile={isMobile}
      />

      {/* Main stage */}
      <TypographicStage {...commonProps} />

      {/* Bottom controls */}
      <BottomBar
        mono={typo.mono}
        playing={playing}
        onPrev={prev}
        onNext={next}
        onTogglePlay={togglePlay}
        onCopy={copyLink}
        copied={copied}
        canPrev={queueRef.current.hasPrev()}
        playBtnRef={playBtnRef}
        isMobile={isMobile}
      />

      {/* Timer line */}
      {showTimer && playing && playBtnRect && (
        <TimerLine
          key={timerKey}
          duration={duration}
          rect={playBtnRect}
        />
      )}

      {/* About overlay */}
      {aboutOpen && (
        <AboutOverlay mono={typo.mono} onClose={() => setAboutOpen(false)} isMobile={isMobile} />
      )}

      {/* Self-hosted audio playlist — shuffled, advances on ended */}
      <audio
        ref={audioElRef}
        onEnded={advanceTrack}
        preload="auto"
        style={{ display: "none" }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top bar — tiny wordmark, audio toggle, about
// ---------------------------------------------------------------------------
function TopBar({ mono, onAbout, audioMuted, onToggleAudio, isMobile }) {
  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: isMobile ? "14px 16px" : "20px 28px",
        zIndex: 10,
        fontFamily: mono,
        fontSize: isMobile ? 10 : 11,
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        color: PALETTE.inkDim,
      }}
    >
      <div style={{ display: "flex", gap: isMobile ? 12 : 20, alignItems: "center" }}>
        <span style={{ color: PALETTE.genji }}>Genji</span>
        <span style={{ color: PALETTE.inkFaint }}>×</span>
        <span style={{ color: PALETTE.quijote }}>Quijote</span>
      </div>
      <div style={{ display: "flex", gap: isMobile ? 14 : 20 }}>
        <button
          onClick={onToggleAudio}
          title={audioMuted ? "Unmute music" : "Mute music"}
          style={chromeBtn(mono)}
        >
          {audioMuted ? "♪ muted" : "♪ playing"}
        </button>
        <button onClick={onAbout} style={chromeBtn(mono)}>
          About
        </button>
      </div>
    </div>
  );
}

function chromeBtn(mono) {
  return {
    background: "transparent",
    border: "none",
    color: PALETTE.inkDim,
    fontFamily: mono,
    fontSize: 11,
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    cursor: "pointer",
    padding: "6px 0",
    transition: "color 0.2s",
    whiteSpace: "nowrap",
  };
}

// ===========================================================================
// VARIATION 1: Typographic — big words, subtle color shift at the seam
// ===========================================================================
function TypographicStage({ pair, typo, playing, typingReveal, sourceOpen, setSourceOpen, fading, isMobile }) {
  const genjiWords = useMemo(() => splitWords(pair.genji_half), [pair]);
  const quijoteWords = useMemo(() => splitWords(pair.quijote_half), [pair]);
  const totalWords = genjiWords.length + quijoteWords.length;

  // Lazy init so the very first render already shows all words. This avoids
  // a flash-of-empty content before the reveal effect has a chance to run.
  const [visibleWords, setVisibleWords] = useState(totalWords);

  // Word-by-word reveal (only while playing)
  useLayoutEffect(() => {
    if (!playing || !typingReveal) {
      setVisibleWords(totalWords);
      return;
    }
    setVisibleWords(0);
    let i = 0;
    const step = () => {
      i++;
      setVisibleWords(i);
      if (i < totalWords) {
        // Word reveals pace — shorter for whitespace chunks
        const next = genjiWords.concat(quijoteWords)[i];
        const delay = /\s/.test(next) ? 36 : 131;
        handle = setTimeout(step, delay);
      }
    };
    let handle = setTimeout(step, 300);
    return () => clearTimeout(handle);
  }, [pair, playing, typingReveal, totalWords, genjiWords, quijoteWords]);

  const renderWord = (chunk, idx, color, shown) => {
    if (/^\s+$/.test(chunk)) return <span key={idx}>{chunk}</span>;
    const visible = idx < shown;
    return (
      <span
        key={idx}
        style={{
          color,
          opacity: visible ? 1 : 0,
          transition: visible ? "opacity 420ms ease-out" : "none",
          display: "inline",
        }}
      >
        {chunk}
      </span>
    );
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: isMobile ? "82px 22px 100px" : "140px 8vw",
        opacity: fading ? 0 : 1,
        transition: "opacity 140ms ease-out",
        // Allow long passages to scroll on small screens rather than overflow.
        overflowY: isMobile ? "auto" : "visible",
      }}
    >
      <div style={{ maxWidth: 1200, width: "100%", position: "relative" }}>
        <p
          key={pair.id}
          style={{
            fontSize: isMobile ? "clamp(20px, 6.2vw, 30px)" : "clamp(28px, 4.2vw, 64px)",
            lineHeight: isMobile ? 1.22 : 1.18,
            letterSpacing: "-0.01em",
            margin: 0,
            textWrap: "pretty",
            fontWeight: typo.displayWeight,
          }}
        >
          {/* Genji half — moss green, slightly faded */}
          <span style={{ color: PALETTE.genji }}>
            {genjiWords.map((w, i) => renderWord(w, i, PALETTE.genji, visibleWords))}
          </span>
          {/* Gentle seam: a hair-wide gradient space, no hard line */}
          <span
            style={{
              color: PALETTE.inkDim,
              padding: "0 0.15em",
            }}
          />
          {/* Quijote half — terracotta */}
          <span style={{ color: PALETTE.quijote }}>
            {quijoteWords.map((w, i) =>
              renderWord(w, i + genjiWords.length, PALETTE.quijote, visibleWords)
            )}
          </span>
        </p>

        {/* Metadata line — chips stay inline, but the InlineSource panel
            below them is absolutely positioned so its expansion doesn't push
            the mashup upward when the user opens a source. */}
        <MetaLine pair={pair} mono={typo.mono} sourceOpen={sourceOpen} setSourceOpen={setSourceOpen} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Metadata line — renders the InlineSource panel
// below the chips when one is active.
// ---------------------------------------------------------------------------
function MetaLine({ pair, mono, sourceOpen, setSourceOpen }) {
  // Clicking the active chip closes the panel; clicking the other swaps to it.
  const onChipClick = (which) => {
    setSourceOpen(sourceOpen === which ? null : which);
  };

  return (
    <div style={{ marginTop: 40, position: "relative" }}>
      <div
        style={{
          display: "flex",
          gap: 24,
          flexWrap: "wrap",
          alignItems: "center",
          fontFamily: mono,
          fontSize: 11,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: PALETTE.inkDim,
        }}
      >
        <span style={{ color: PALETTE.inkFaint }}>#{pair.id}</span>
        <button
          onClick={() => onChipClick("genji")}
          style={metaChipStyle(
            PALETTE.genji,
            mono,
            sourceOpen === "genji"
          )}
          title="Reveal the original Genji sentence"
        >
          <span style={{ color: PALETTE.inkFaint, marginRight: 6 }}>Genji</span>
          {formatChapter(pair.genji_meta?.chapter)}
        </button>
        <button
          onClick={() => onChipClick("quijote")}
          style={metaChipStyle(
            PALETTE.quijote,
            mono,
            sourceOpen === "quijote"
          )}
          title="Reveal the original Quijote sentence"
        >
          <span style={{ color: PALETTE.inkFaint, marginRight: 6 }}>Quijote</span>
          {formatChapter(pair.quijote_meta?.chapter)}
        </button>
      </div>

      {/* Inline source panel — visible when a side is active */}
      <InlineSource pair={pair} which={sourceOpen} mono={mono} />
    </div>
  );
}

function metaChipStyle(color, mono, active) {
  return {
    background: "transparent",
    border: "none",
    padding: "4px 0",
    cursor: "pointer",
    fontFamily: mono,
    fontSize: 11,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color,
    borderBottom: active ? `1px solid ${color}` : `1px dotted ${color}40`,
    transition: "opacity 0.2s, border-bottom 0.2s",
  };
}

// ---------------------------------------------------------------------------
// Inline source panel — expands smoothly below the meta line when a chapter
// chip is active. Renders the original sentence with the clipped half tinted
// in the side's color, the rest in dim ink.
// ---------------------------------------------------------------------------
function InlineSource({ pair, which, mono }) {
  const isMobile = useIsMobile();
  // Keep the previous content rendered during the collapse so the height
  // animation has something to fade out from.
  const [renderedWhich, setRenderedWhich] = useState(which);
  // Dynamically measure available space between the panel's top edge and the
  // bottom nav so long sources never overlap the controls.
  const wrapRef = useRef(null);
  const [maxH, setMaxH] = useState(600);
  useEffect(() => {
    if (which) setRenderedWhich(which);
  }, [which]);

  useEffect(() => {
    if (!which) return;
    const measure = () => {
      const el = wrapRef.current;
      if (!el) return;
      const top = el.getBoundingClientRect().top;
      // Bottom nav is ~80px tall (with its 40px gradient-fade top); leave
      // 16px breathing room above where the fade starts to read. We always
      // hard-cap the panel to this so it can never poke below the nav,
      // regardless of how short the actual content is.
      const avail = window.innerHeight - top - 100 - 16;
      setMaxH(Math.max(60, Math.min(600, avail)));
    };
    // Measure now AND after the open animation settles, so the cap reflects
    // the panel's true top once expanded.
    measure();
    const t1 = setTimeout(measure, 60);
    const t2 = setTimeout(measure, 360);
    window.addEventListener("resize", measure);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener("resize", measure);
    };
  }, [which, renderedWhich, pair]);

  const open = !!which;
  const w = renderedWhich;
  if (!w) {
    // Nothing has ever been opened — render an empty closed container so the
    // first open can animate from height 0.
    return (
      <div
        style={{
          maxHeight: 0,
          overflow: "hidden",
          transition: "max-height 280ms ease, opacity 200ms ease",
          opacity: 0,
        }}
      />
    );
  }

  const isGenji = w === "genji";
  const color = isGenji ? PALETTE.genji : PALETTE.quijote;
  const source = (isGenji ? pair.genji_source : pair.quijote_source) || "";
  const half = (isGenji ? pair.genji_half : pair.quijote_half) || "";
  const sourceText = source.replace(/\n/g, " ");
  const idx = sourceText.indexOf(half);
  let before = "", matched = sourceText, after = "";
  if (idx >= 0) {
    before = sourceText.slice(0, idx);
    matched = sourceText.slice(idx, idx + half.length);
    after = sourceText.slice(idx + half.length);
  }

  return (
    <div
      ref={wrapRef}
      style={{
        // Anchored absolutely below the meta chips so opening it doesn't
        // shift the mashup. Sits 18px below the chip row.
        position: "absolute",
        top: "100%",
        left: 0,
        right: 0,
        // Cap height so the panel never overlaps the fixed bottom nav.
        // maxH is measured from the panel's top edge to the nav.
        maxHeight: open ? maxH : 0,
        opacity: open ? 1 : 0,
        overflow: "hidden auto",
        transition: "max-height 320ms ease, opacity 220ms ease",
        marginTop: open ? 18 : 0,
        pointerEvents: open ? "auto" : "none",
      }}
    >
      <div
        style={{
          paddingTop: 16,
          borderTop: `1px solid ${PALETTE.line}`,
        }}
      >
        <p
          style={{
            fontSize: isMobile ? 16 : 20,
            lineHeight: 1.6,
            color: PALETTE.inkDim,
            margin: 0,
            textWrap: "pretty",
            maxWidth: 760,
            fontFamily: "inherit",
          }}
        >
          {before}
          <span style={{ color, fontWeight: 500 }}>{matched}</span>
          {after}
        </p>
        <div
          style={{
            marginTop: 14,
            fontFamily: mono,
            fontSize: 10,
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            color,
            maxWidth: 760,
          }}
        >
          — {isGenji ? "The Tale of Genji" : "Don Quijote"}
        </div>
      </div>
    </div>
  );
}


// ===========================================================================
// Bottom control bar
// ===========================================================================
function BottomBar({ mono, playing, onPrev, onNext, onTogglePlay, onCopy, copied, canPrev, playBtnRef, isMobile }) {
  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: isMobile ? 18 : 40,
        padding: isMobile ? "18px 14px 18px" : "22px 28px 24px",
        zIndex: 10,
        fontFamily: mono,
        fontSize: isMobile ? 10 : 11,
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        color: PALETTE.inkDim,
        // Solid backdrop so content above (e.g. inline source panel) doesn't
        // bleed visibly behind the nav controls. Soft fade at the top edge.
        background: `linear-gradient(to top, ${PALETTE.bg} 0%, ${PALETTE.bg} 70%, ${PALETTE.bg}00 100%)`,
        paddingTop: isMobile ? 32 : 40,
      }}
    >
      <button
        onClick={onPrev}
        disabled={!canPrev}
        style={{
          ...chromeBtn(mono),
          opacity: canPrev ? 1 : 0.25,
          padding: isMobile ? "10px 12px" : "6px 0",
          fontSize: isMobile ? 16 : 11,
          minWidth: isMobile ? 44 : "auto",
        }}
        title="Previous"
      >
        {isMobile ? "←" : "← Prev"}
      </button>

      {/* Play/Pause — the distinct one, visually differentiated from the audio toggle */}
      <button
        ref={playBtnRef}
        onClick={onTogglePlay}
        style={{
          ...chromeBtn(mono),
          border: `1px solid ${PALETTE.inkFaint}`,
          padding: isMobile ? "7px 14px" : "8px 18px",
          color: PALETTE.ink,
          letterSpacing: "0.15em",
          minWidth: isMobile ? 88 : 108,
          fontSize: isMobile ? 10 : 11,
        }}
      >
        {playing ? "❚❚ Pause" : "▸ Play"}
      </button>

      <button
        onClick={onNext}
        style={{
          ...chromeBtn(mono),
          padding: isMobile ? "10px 12px" : "6px 0",
          fontSize: isMobile ? 16 : 11,
          minWidth: isMobile ? 44 : "auto",
        }}
        title="Next"
      >
        {isMobile ? "→" : "Next →"}
      </button>

      <div style={{ width: 1, height: isMobile ? 14 : 18, background: PALETTE.line }} />

      {/* Fixed-width share button to avoid jumping when label changes to "Copied" */}
      <button
        onClick={onCopy}
        style={{ ...chromeBtn(mono), minWidth: isMobile ? 56 : 70, textAlign: "center" }}
        title="Copy shareable link"
      >
        {copied ? "✓ Copied" : "Share"}
      </button>
    </div>
  );
}

// ===========================================================================
// Timer line — thin depleting line at the very bottom
// ===========================================================================
function TimerLine({ duration, rect }) {
  // Bound to the Play button's width — the line breathes underneath the
  // control it represents, grounding the countdown in its source.
  return (
    <div
      style={{
        position: "fixed",
        left: rect.left,
        width: rect.width,
        bottom: Math.max(6, window.innerHeight - rect.bottom - 6),
        height: 1,
        zIndex: 11,
        pointerEvents: "none",
        background: "rgba(255,255,255,0.06)",
      }}
    >
      <div
        style={{
          height: "100%",
          width: "100%",
          background: `linear-gradient(to right, ${PALETTE.genji}, ${PALETTE.quijote})`,
          transformOrigin: "left",
          animation: `deplete ${duration}ms linear forwards`,
        }}
      />
    </div>
  );
}

// ===========================================================================
// About overlay
// ===========================================================================
function AboutOverlay({ mono, onClose, isMobile }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(10, 10, 8, 0.94)",
        backdropFilter: "blur(6px)",
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: isMobile ? "24px 16px" : "60px 32px",
        animation: "fadeIn 240ms ease-out",
        overflowY: "auto",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: 640,
          width: "100%",
          background: PALETTE.bgAlt,
          border: `1px solid ${PALETTE.line}`,
          padding: isMobile ? "32px 24px" : "48px 52px",
          position: "relative",
        }}
      >
        <div
          style={{
            fontFamily: mono,
            fontSize: 10,
            letterSpacing: "0.24em",
            textTransform: "uppercase",
            color: PALETTE.inkDim,
            marginBottom: 20,
          }}
        >
          About
        </div>
        <h2
          style={{
            fontSize: isMobile ? 22 : 28,
            lineHeight: 1.2,
            margin: "0 0 28px",
            color: PALETTE.ink,
            fontWeight: 400,
          }}
        >
          The Shining Prince <span style={{ color: PALETTE.inkDim }}>meets</span> The Knight Errant
        </h2>

        <p
          style={{
            fontSize: 15,
            lineHeight: 1.7,
            color: PALETTE.inkDim,
            margin: "0 0 16px",
          }}
        >
          Lorem ipsum Lorem ipsum Lorem ipsum Lorem ipsum Lorem ipsum — some
          explanation of the background. Each mashup joins the first half of a
          sentence from Murasaki Shikibu's <em>Tale of Genji</em> with the second
          half of a sentence from Cervantes' <em>Don Quijote</em>.
        </p>
        <p
          style={{
            fontSize: 15,
            lineHeight: 1.7,
            color: PALETTE.inkDim,
            margin: "0 0 28px",
          }}
        >
          Lorem ipsum Lorem ipsum Lorem ipsum Lorem ipsum Lorem ipsum — some
          explanation of the background. Both texts in the public domain via
          Project Gutenberg.
        </p>

        {/* Legend */}
        <div
          style={{
            display: "flex",
            gap: 28,
            padding: "16px 0",
            borderTop: `1px solid ${PALETTE.line}`,
            borderBottom: `1px solid ${PALETTE.line}`,
            margin: "0 0 28px",
            fontFamily: mono,
            fontSize: 11,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 12, height: 12, background: PALETTE.genji }} />
            <span style={{ color: PALETTE.inkDim }}>Genji</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 12, height: 12, background: PALETTE.quijote }} />
            <span style={{ color: PALETTE.inkDim }}>Quijote</span>
          </div>
        </div>

        {/* Links */}
        <div
          style={{
            fontFamily: mono,
            fontSize: 11,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: PALETTE.inkFaint,
            marginBottom: 10,
          }}
        >
          Blog post
        </div>
        <div style={{ marginBottom: 24 }}>
          <a href="#" style={linkStyle}>
            A note on the exquisite-corpse technique →
          </a>
        </div>

        <div
          style={{
            fontFamily: mono,
            fontSize: 11,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: PALETTE.inkFaint,
            marginBottom: 10,
          }}
        >
          Related
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <a href="#" style={linkStyle}>The Lexicorium →</a>
          <a href="#" style={linkStyle}>The Memory Palace →</a>
          <a href="#" style={linkStyle}>Colorless green ideas →</a>
        </div>

        {/* Keyboard shortcuts — desktop only (mobile has no keyboard) */}
        {!isMobile && (
          <div
            style={{
              marginTop: 32,
              paddingTop: 20,
              borderTop: `1px solid ${PALETTE.line}`,
              fontFamily: mono,
              fontSize: 10,
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              color: PALETTE.inkFaint,
              display: "flex",
              gap: 18,
              flexWrap: "wrap",
            }}
          >
            <span>← → Navigate</span>
            <span>Space Play/Pause</span>
            <span>i About</span>
            <span>Esc Close</span>
          </div>
        )}

        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: 20,
            right: 20,
            background: "transparent",
            border: "none",
            color: PALETTE.inkDim,
            fontFamily: mono,
            fontSize: 11,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            cursor: "pointer",
          }}
        >
          ✕ Close
        </button>
      </div>
    </div>
  );
}

const linkStyle = {
  color: PALETTE.ink,
  textDecoration: "none",
  borderBottom: `1px solid ${PALETTE.line}`,
  paddingBottom: 2,
  fontSize: 15,
  fontFamily: "inherit",
};

// ===========================================================================
// Boot
// ===========================================================================
window.BOOT_APP = function boot(data) {
  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(<App tweakValues={TWEAK_DEFAULTS} pairs={data.pairs} />);
};
