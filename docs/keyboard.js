/**
 * keyboard.js — Keyboard shortcut bindings for the Genji-Quijote player.
 *
 * Attaches a single keydown listener to the document and dispatches to the
 * appropriate callback based on the key pressed.
 */

/**
 * Binds keyboard shortcuts to the provided callbacks.
 *
 * Shortcuts:
 *   ArrowRight — call onNext
 *   ArrowLeft  — call onPrev
 *   Space      — call onTogglePlay (default scroll behaviour prevented)
 *
 * @param {Object} handlers - Object containing callback functions.
 * @param {Function} handlers.onNext - Called when ArrowRight is pressed.
 * @param {Function} handlers.onPrev - Called when ArrowLeft is pressed.
 * @param {Function} handlers.onTogglePlay - Called when Space is pressed.
 * @returns {Function} cleanup - Call this function to remove the event
 *   listener and unbind all shortcuts.
 */
export function bindKeys({ onNext, onPrev, onTogglePlay }) {
  /**
   * Handles keydown events and dispatches to the relevant callback.
   *
   * @param {KeyboardEvent} event - The browser keydown event.
   * @returns {void}
   */
  function handleKeyDown(event) {
    switch (event.key) {
      case 'ArrowRight':
        onNext();
        break;
      case 'ArrowLeft':
        onPrev();
        break;
      case ' ':
        // Space bar would scroll the page by default — suppress that.
        event.preventDefault();
        onTogglePlay();
        break;
      // All other keys are intentionally ignored.
    }
  }

  document.addEventListener('keydown', handleKeyDown);

  /**
   * Removes the keydown event listener, unbinding all shortcuts registered
   * by this call to bindKeys.
   *
   * @returns {void}
   */
  function cleanup() {
    document.removeEventListener('keydown', handleKeyDown);
  }

  return cleanup;
}
