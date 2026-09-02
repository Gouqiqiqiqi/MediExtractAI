/**
 * "Something about the runs changed" — announced to whoever is showing a count
 * of them.
 *
 * The sidebar's badge is the answer to "is anyone behind?", and it was only
 * re-read on navigation: sign a run off in the pop-up and the badge went on
 * claiming the work was outstanding until you happened to click something else.
 * A count that lags the action it counts teaches people to distrust it.
 *
 * A window event rather than a context: the publishers are scattered across
 * pages and dialogs, the only subscriber is the shell around them, and neither
 * needs to re-render the other.
 */

const TOPIC = 'mediextract:runs-changed';

/** Call after a run is created, signed off, rejected, reopened or discarded. */
export function runsChanged(): void {
  window.dispatchEvent(new Event(TOPIC));
}

export function onRunsChanged(handler: () => void): () => void {
  window.addEventListener(TOPIC, handler);
  return () => window.removeEventListener(TOPIC, handler);
}
