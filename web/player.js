/**
 * player.js — Auto-advance timer for the Genji-Quijote pair display.
 *
 * Calculates a reading-time-based duration from a pair's word count and fires
 * a callback after that duration, enabling hands-free playback.
 */

/**
 * Creates an auto-advance player that fires `onAdvance` after a duration
 * derived from the word count of the current pair.
 *
 * Duration formula: Math.max(minDuration, (wordCount / wpm) * 60000)
 *
 * @param {Function} onAdvance - Zero-argument callback invoked when the timer
 *   fires. The caller is responsible for advancing the queue and re-rendering.
 * @param {number} [wpm=200] - Reading speed in words per minute used to
 *   calculate display duration.
 * @param {number} [minDuration=4000] - Minimum display duration in
 *   milliseconds, applied regardless of word count.
 * @returns {{ start: Function, stop: Function, isPlaying: Function }}
 */
export function createPlayer(onAdvance, wpm = 200, minDuration = 4000) {
  // The active setTimeout handle, or null when no timer is running.
  let timerId = null;

  /**
   * Begins the countdown for a pair with the given word count.
   *
   * Cancels any existing timer first (so calling start() mid-play safely
   * resets the countdown for a new pair rather than stacking timeouts).
   *
   * @param {number} wordCount - Number of words in the pair's display text.
   * @returns {void}
   */
  function start(wordCount) {
    // Always clear an existing timer before setting a new one to avoid
    // multiple concurrent timeouts if start() is called more than once.
    stop();

    // Compute reading duration, enforcing the minimum floor.
    const duration = Math.max(minDuration, (wordCount / wpm) * 60000);

    timerId = setTimeout(() => {
      // Mark as stopped before invoking the callback so that isPlaying()
      // returns false if the callback calls stop() or inspects state.
      timerId = null;
      onAdvance();
    }, duration);
  }

  /**
   * Cancels the running timer and marks the player as not playing.
   *
   * Safe to call when no timer is active (no-op in that case).
   *
   * @returns {void}
   */
  function stop() {
    if (timerId !== null) {
      clearTimeout(timerId);
      timerId = null;
    }
  }

  /**
   * Returns whether the player currently has an active countdown running.
   *
   * @returns {boolean} True if a timer is active, false otherwise.
   */
  function isPlaying() {
    return timerId !== null;
  }

  return { start, stop, isPlaying };
}
