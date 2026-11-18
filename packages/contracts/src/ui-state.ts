/**
 * Route state contract. Every route in the platform .nventory renders one of
 * these states, and every non-success state must answer the same three
 * questions: what is unavailable, what is cached or last known, and what the
 * user can safely do next.
 */

export const UI_STATES = [
  "loading",
  "success",
  "empty",
  "stale",
  "degraded",
  "forbidden",
  "timeout",
  "policy_blocked",
  "error",
] as const;

export type UiState = (typeof UI_STATES)[number];

export function isUiState(value: unknown): value is UiState {
  return typeof value === "string" && (UI_STATES as readonly string[]).includes(value);
}

/**
 * The copy a non-success state must carry. `lastKnown` is nullable because
 * "nothing cached yet" is a legitimate answer, but it must be answered
 * explicitly rather than left undefined.
 */
export interface StateCopy {
  /** What is unavailable, in the user's terms. */
  unavailable: string;
  /** What cached or last-known data is being shown instead, or null when none. */
  lastKnown: string | null;
  /** The safe next action available to this user. */
  nextAction: string;
}

export type ViewState<T> =
  | { state: "success"; data: T }
  | { state: "loading" }
  | { state: Exclude<UiState, "success" | "loading">; copy: StateCopy; data: T | null };

export function isNonSuccessState(state: UiState): boolean {
  return state !== "success" && state !== "loading";
}

/**
 * Returns the reasons a non-success state's copy is inadequate, empty when
 * valid. A test asserts every route's non-success states pass this, which is
 * what stops "Something went wrong" from shipping.
 */
export function validateStateCopy(copy: StateCopy): string[] {
  const problems: string[] = [];

  if (copy.unavailable.trim() === "") {
    problems.push("state copy must say what is unavailable");
  }

  if (copy.nextAction.trim() === "") {
    problems.push("state copy must offer a safe next action");
  }

  // `lastKnown === null` is valid (nothing cached); an empty string is not,
  // because it means the question was skipped rather than answered.
  if (copy.lastKnown !== null && copy.lastKnown.trim() === "") {
    problems.push("state copy lastKnown must be null or a real description");
  }

  return problems;
}
