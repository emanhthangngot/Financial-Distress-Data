/**
 * The educational disclaimer is a coursework requirement, not decoration. It is
 * defined once here so the string cannot drift between surfaces and so a test
 * can assert it renders on every decision-support surface.
 */

export const DISCLAIMER_TEXT =
  "Nội dung phục vụ mục đích học tập, không phải khuyến nghị đầu tư.";

/**
 * Surfaces that must render the disclaimer. Sourced from the phase-02
 * requirement: company, explanation, AI chat, comparison and exported report.
 */
export const DISCLAIMER_SURFACES = [
  "company",
  "model_explanation",
  "agent_chat",
  "compare",
  "report_export",
] as const;

export type DisclaimerSurface = (typeof DISCLAIMER_SURFACES)[number];

export function requiresDisclaimer(surface: string): surface is DisclaimerSurface {
  return (DISCLAIMER_SURFACES as readonly string[]).includes(surface);
}
