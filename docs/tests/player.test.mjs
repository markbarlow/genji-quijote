/**
 * player.test.mjs — Smoke tests for web/player.js
 *
 * Run from the repo root with:
 *   node web/tests/player.test.mjs
 */

import assert from 'assert';
import { createPlayer } from '../player.js';

// ---------------------------------------------------------------------------
// Test 1 — createPlayer returns an object with start, stop, isPlaying methods
// ---------------------------------------------------------------------------
{
  const player = createPlayer(() => {});
  assert.strictEqual(typeof player.start, 'function', 'start should be a function');
  assert.strictEqual(typeof player.stop, 'function', 'stop should be a function');
  assert.strictEqual(typeof player.isPlaying, 'function', 'isPlaying should be a function');
  console.log('PASS test 1: createPlayer returns object with start, stop, isPlaying');
}

// ---------------------------------------------------------------------------
// Test 2 — isPlaying() is false before start() is called
// ---------------------------------------------------------------------------
{
  const player = createPlayer(() => {});
  assert.strictEqual(player.isPlaying(), false, 'isPlaying() should be false before start()');
  console.log('PASS test 2: isPlaying() is false before start() is called');
}

// ---------------------------------------------------------------------------
// Test 3 — isPlaying() is true after start() is called with a word count
// ---------------------------------------------------------------------------
{
  const player = createPlayer(() => {}, 99999, 50);
  player.start(10);
  assert.strictEqual(player.isPlaying(), true, 'isPlaying() should be true after start()');
  // Clean up the timer so it does not fire during subsequent tests.
  player.stop();
  console.log('PASS test 3: isPlaying() is true after start() is called');
}

// ---------------------------------------------------------------------------
// Test 4 — isPlaying() is false after stop() is called
// ---------------------------------------------------------------------------
{
  const player = createPlayer(() => {}, 99999, 50);
  player.start(10);
  player.stop();
  assert.strictEqual(player.isPlaying(), false, 'isPlaying() should be false after stop()');
  console.log('PASS test 4: isPlaying() is false after stop() is called');
}

// ---------------------------------------------------------------------------
// Test 5 — onAdvance callback fires after the expected duration
//
// Use minDuration=50 and wpm=99999 so the word-count path is negligible and
// the timer fires after ~50 ms. Wait 100 ms to give it plenty of margin.
// ---------------------------------------------------------------------------
{
  await new Promise((resolve, reject) => {
    let fired = false;

    const player = createPlayer(() => {
      fired = true;
    }, 99999, 50);

    player.start(1);

    setTimeout(() => {
      if (fired) {
        console.log('PASS test 5: onAdvance callback fires after expected duration');
        resolve();
      } else {
        reject(new Error('onAdvance was not called within 100 ms'));
      }
    }, 100);
  });
}

// ---------------------------------------------------------------------------
console.log('\nAll player tests passed.');
