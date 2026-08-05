import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// Testing Library's auto-cleanup only registers itself when it detects a
// global `afterEach` (as Jest provides). Vitest exposes one only in `globals`
// mode, which this project does not enable, so the unmount has to be wired
// explicitly — otherwise every render in a file after the first accumulates
// in `document.body` and queries start matching more than one element.
afterEach(() => cleanup());

// jsdom does not implement matchMedia. The assistant panel uses it to decide
// whether the docked view is modal on small screens; tests run at jsdom's
// default (desktop-sized) viewport, so "matches: false" is the honest answer.
// jsdom does not implement scrollTo either. The assistant panel's thread
// keeps the latest turn in view by calling it; a no-op is the honest stand-in
// since jsdom has no real layout to scroll.
if (typeof Element.prototype.scrollTo !== "function") {
  Element.prototype.scrollTo = () => {};
}

if (typeof window.matchMedia !== "function") {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}
