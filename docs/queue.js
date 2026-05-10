/**
 * queue.js — Fisher-Yates depletion queue for Genji-Quijote pair navigation.
 *
 * Ensures no pair repeats within a configurable window of recently-shown pairs,
 * and supports backward navigation through a played history stack.
 */

/**
 * Shuffles an array in place using the Fisher-Yates algorithm.
 *
 * @param {Array} arr - The array to shuffle.
 * @returns {Array} The same array, shuffled in place.
 */
function shuffle(arr) {
  // Walk from the end toward the beginning, swapping each element with a
  // randomly chosen element at or before it.
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = arr[i];
    arr[i] = arr[j];
    arr[j] = tmp;
  }
  return arr;
}

/**
 * Creates a depletion queue over a pool of pair objects.
 *
 * The queue draws pairs without repetition within the last `windowSize` shown
 * pairs, and supports prev/next navigation through a history stack.
 *
 * @param {Array<{id: string|number}>} pairs - Array of pair objects; each must
 *   have at least an `id` field.
 * @param {number} [windowSize=30] - How many recently-seen pair IDs to exclude
 *   from the next shuffle cycle.
 * @returns {{next: Function, prev: Function, current: Function, hasPrev: Function}}
 */
export function createQueue(pairs, windowSize = 30) {
  // `remaining` holds pairs not yet drawn in the current shuffle cycle.
  // Starts empty so that the first call to next() triggers an immediate refill.
  let remaining = [];

  // Circular buffer of recently shown pair IDs, oldest at index 0.
  let recentIds = [];

  // All pairs shown so far in this session, in chronological order.
  const history = [];

  // Pointer into history. -1 means no pair has been shown yet.
  let historyIndex = -1;

  /**
   * Refills `remaining` by collecting all pairs whose IDs are not in
   * `recentIds`, then Fisher-Yates shuffling them.
   *
   * If every pair is excluded (pool smaller than windowSize), `recentIds` is
   * cleared and all pairs are used, preventing a deadlock.
   */
  function refill() {
    const recentSet = new Set(recentIds);
    let candidates = pairs.filter(p => !recentSet.has(p.id));

    // Guard against a pool smaller than windowSize — clear the exclusion window
    // so we always have something to draw from.
    if (candidates.length === 0) {
      recentIds = [];
      candidates = pairs.slice(); // copy so we don't mutate the source array
    }

    remaining = shuffle(candidates);
  }

  /**
   * Draws the next pair from the pool, managing the depletion cycle.
   *
   * If the user has gone back in history (historyIndex is not at the end),
   * this replays the already-seen pair at the next history position instead
   * of drawing a new one.
   *
   * @returns {{id: *, [key: string]: *}} The next pair object.
   */
  function next() {
    // Re-play: user navigated backward and is now moving forward again through
    // already-seen history rather than drawing a fresh pair.
    if (historyIndex < history.length - 1) {
      historyIndex++;
      return history[historyIndex];
    }

    // Draw a new pair from the depletion pool.
    if (remaining.length === 0) {
      refill();
    }

    // Pop from the end of the shuffled array (O(1) removal).
    const pair = remaining.pop();

    // Track recency. Shift off the oldest entry if we exceed the window size.
    recentIds.push(pair.id);
    if (recentIds.length > windowSize) {
      recentIds.shift();
    }

    history.push(pair);
    historyIndex = history.length - 1;
    return pair;
  }

  /**
   * Moves backward in history and returns the previous pair.
   *
   * @returns {{id: *, [key: string]: *}|null} The previous pair object, or
   *   null if already at the beginning of history.
   */
  function prev() {
    if (historyIndex > 0) {
      historyIndex--;
      return history[historyIndex];
    }
    return null;
  }

  /**
   * Returns the pair currently pointed to by historyIndex without advancing.
   *
   * @returns {{id: *, [key: string]: *}|null} The current pair object, or null
   *   if no pair has been shown yet.
   */
  function current() {
    if (history.length === 0) {
      return null;
    }
    return history[historyIndex];
  }

  /**
   * Returns whether there is a previous pair to navigate back to.
   *
   * @returns {boolean} True if historyIndex > 0.
   */
  function hasPrev() {
    return historyIndex > 0;
  }

  return { next, prev, current, hasPrev };
}
