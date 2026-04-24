/**
 * queue.test.mjs — Unit tests for web/queue.js
 *
 * Run from the repo root with:
 *   node web/tests/queue.test.mjs
 */

import assert from 'assert';
import { createQueue } from '../queue.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Builds a simple pool of pair objects with sequential numeric IDs.
 *
 * @param {number} n - Number of pairs to create.
 * @returns {Array<{id: number, label: string}>} Array of pair objects.
 */
function makePairs(n) {
  return Array.from({ length: n }, (_, i) => ({ id: i, label: `pair-${i}` }));
}

// ---------------------------------------------------------------------------
// Test 1 — next() returns a pair object with an id field
// ---------------------------------------------------------------------------
{
  const pool = makePairs(5);
  const q = createQueue(pool);
  const p = q.next();
  assert.ok(p !== null && p !== undefined, 'next() should return a value');
  assert.ok('id' in p, 'returned pair should have an id field');
  console.log('PASS test 1: next() returns a pair with an id field');
}

// ---------------------------------------------------------------------------
// Test 2 — calling next() N times where N = pool size returns N distinct pairs
// ---------------------------------------------------------------------------
{
  const n = 10;
  const pool = makePairs(n);
  // Use a windowSize larger than n so no pair is excluded during the cycle.
  const q = createQueue(pool, n + 5);
  const seen = new Set();
  for (let i = 0; i < n; i++) {
    const p = q.next();
    assert.ok(!seen.has(p.id), `Duplicate id ${p.id} found before pool depleted`);
    seen.add(p.id);
  }
  assert.strictEqual(seen.size, n, 'Should have seen every pair exactly once');
  console.log('PASS test 2: full depletion cycle yields N distinct pairs');
}

// ---------------------------------------------------------------------------
// Test 3 — after depleting the pool, next() continues returning pairs (refill)
// ---------------------------------------------------------------------------
{
  const pool = makePairs(5);
  const q = createQueue(pool, 0); // windowSize=0 so all pairs are always candidates
  // Exhaust the first cycle.
  for (let i = 0; i < 5; i++) q.next();
  // The 6th call should succeed and return a valid pair.
  const p = q.next();
  assert.ok(p !== null && 'id' in p, 'next() should still return a pair after refill');
  console.log('PASS test 3: next() continues after pool depletion (refill works)');
}

// ---------------------------------------------------------------------------
// Test 4 — no pair repeats within a window of windowSize calls to next()
//           (windowSize=5, pool=20)
// ---------------------------------------------------------------------------
{
  const windowSize = 5;
  const pool = makePairs(20);
  const q = createQueue(pool, windowSize);

  // Draw enough pairs to span multiple refill cycles.
  const totalDraws = 60;
  const recentWindow = [];

  for (let i = 0; i < totalDraws; i++) {
    const p = q.next();
    // Check the pair's id does not appear in the preceding `windowSize` draws.
    const windowIds = recentWindow.slice(-windowSize);
    assert.ok(
      !windowIds.includes(p.id),
      `Pair id ${p.id} repeated within window at draw ${i}`
    );
    recentWindow.push(p.id);
  }
  console.log('PASS test 4: no pair repeats within the recency window');
}

// ---------------------------------------------------------------------------
// Test 5 — prev() returns null when at the start of history
// ---------------------------------------------------------------------------
{
  const pool = makePairs(5);
  const q = createQueue(pool);
  assert.strictEqual(q.prev(), null, 'prev() should return null before any next()');
  q.next();
  // After one next(), historyIndex is 0 — still at the start.
  assert.strictEqual(q.prev(), null, 'prev() should return null when at index 0');
  console.log('PASS test 5: prev() returns null at start of history');
}

// ---------------------------------------------------------------------------
// Test 6 — prev() after two next() calls returns the first pair shown
// ---------------------------------------------------------------------------
{
  const pool = makePairs(10);
  const q = createQueue(pool);
  const first = q.next();
  q.next();
  const back = q.prev();
  assert.strictEqual(back.id, first.id, 'prev() should return the first pair shown');
  console.log('PASS test 6: prev() after two next() calls returns the first pair');
}

// ---------------------------------------------------------------------------
// Test 7 — hasPrev() returns false before navigation, true after one next()
// ---------------------------------------------------------------------------
{
  const pool = makePairs(5);
  const q = createQueue(pool);
  assert.strictEqual(q.hasPrev(), false, 'hasPrev() should be false initially');
  q.next();
  // Still at index 0 after one call — no previous entry.
  assert.strictEqual(q.hasPrev(), false, 'hasPrev() should be false after exactly one next()');
  q.next();
  // Now at index 1 — there is a previous entry.
  assert.strictEqual(q.hasPrev(), true, 'hasPrev() should be true after two next() calls');
  console.log('PASS test 7: hasPrev() returns correct values');
}

// ---------------------------------------------------------------------------
// Test 8 — current() returns null before any next(), then matches last next()
// ---------------------------------------------------------------------------
{
  const pool = makePairs(5);
  const q = createQueue(pool);
  assert.strictEqual(q.current(), null, 'current() should be null before any next()');
  const p = q.next();
  assert.strictEqual(q.current().id, p.id, 'current() should match the last next() result');
  const p2 = q.next();
  assert.strictEqual(q.current().id, p2.id, 'current() should update after second next()');
  console.log('PASS test 8: current() returns null then tracks last next() result');
}

// ---------------------------------------------------------------------------
// Test 9 — after prev(), calling next() re-plays the already-seen pair
// ---------------------------------------------------------------------------
{
  const pool = makePairs(10);
  const q = createQueue(pool);
  const first = q.next();
  const second = q.next();
  // Go back.
  q.prev(); // now at first
  // Going forward should replay second, not draw a new pair.
  const replayed = q.next();
  assert.strictEqual(replayed.id, second.id, 'next() after prev() should replay the already-seen pair');
  console.log('PASS test 9: next() after prev() re-plays the already-seen pair');
}

// ---------------------------------------------------------------------------
// Test 10 — works correctly with a pool smaller than windowSize
//            (windowSize=10, pool=3)
// ---------------------------------------------------------------------------
{
  const pool = makePairs(3);
  const q = createQueue(pool, 10); // windowSize larger than pool
  // Draw many pairs — should never get stuck.
  const draws = 15;
  for (let i = 0; i < draws; i++) {
    const p = q.next();
    assert.ok(p !== null && 'id' in p, `Draw ${i}: expected a valid pair`);
    assert.ok(
      pool.some(pp => pp.id === p.id),
      `Draw ${i}: returned id ${p.id} not in pool`
    );
  }
  console.log('PASS test 10: works correctly with pool smaller than windowSize');
}

// ---------------------------------------------------------------------------
console.log('\nAll queue tests passed.');
