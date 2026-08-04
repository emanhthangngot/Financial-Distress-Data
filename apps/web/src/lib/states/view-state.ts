import type { StateCopy, ViewState } from "@distresslens/contracts";

/**
 * Reading a `ViewState` in a page.
 *
 * Every route asks the same two questions — is there data to render, and is
 * there a state to explain — and `ViewState` is a discriminated union that
 * TypeScript will not narrow through an inline ternary. These two helpers keep
 * that narrowing in one place rather than in six pages that could each get it
 * subtly wrong.
 */

/** The data to render, or null when the state carries none. */
export function viewData<T>(view: ViewState<T>): T | null {
  return view.state === "loading" ? null : view.data;
}

/**
 * The copy explaining this state, or null when the state is success and needs
 * no explanation. Loading is answered by the caller's surface-specific copy,
 * because "what is loading" is a fact about the page, not about the port.
 */
export function viewCopy<T>(view: ViewState<T>, loadingCopy: StateCopy): StateCopy | null {
  if (view.state === "success") {
    return null;
  }
  return view.state === "loading" ? loadingCopy : view.copy;
}

/** True when the state should be rendered as a failure rather than a caveat. */
export function isFailureState<T>(view: ViewState<T>): boolean {
  return view.state === "error";
}
