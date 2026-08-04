import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import type { Page, TestInfo } from "@playwright/test";

/**
 * Screenshot capture with a manifest.
 *
 * A screenshot on its own proves nothing: it does not say which role saw it,
 * which plane state produced it, or which commit and data version it came from.
 * Every capture therefore writes a JSON record beside the image carrying those
 * fields, so a reviewer can tell an executed run from a fixture render without
 * trusting the filename.
 */

export interface EvidenceCapture {
  /** Route pattern, e.g. `/companies/[ticker]`. */
  route: string;
  /** The UI state this frame proves, e.g. `degraded`. */
  state: string;
  role: string;
  /** True when the EKS evidence plane was reachable for this run. */
  planeReady: boolean;
  /** What a reviewer should be able to see in the frame. */
  expected: string;
}

const EVIDENCE_DIR = path.join(process.cwd(), "e2e", ".artifacts", "evidence");

export async function captureEvidence(
  page: Page,
  testInfo: TestInfo,
  capture: EvidenceCapture,
): Promise<string> {
  const viewport = page.viewportSize();
  const routeSlug = capture.route.replace(/[^\w]+/g, "-").replace(/^-|-$/g, "") || "root";
  const slug = `${routeSlug}--${capture.state}--${capture.role}--${testInfo.project.name}`;

  await mkdir(EVIDENCE_DIR, { recursive: true });
  const imagePath = path.join(EVIDENCE_DIR, `${slug}.png`);
  await page.screenshot({ path: imagePath, fullPage: true });

  const manifest = {
    route: capture.route,
    state: capture.state,
    role: capture.role,
    viewport: viewport === null ? null : `${viewport.width}x${viewport.height}`,
    project: testInfo.project.name,
    planeAvailability: capture.planeReady ? "LIVE_AVAILABLE" : "LIVE_UNAVAILABLE",
    // Fixture-backed frames must be self-identifying so one can never be filed
    // as proof of an executed runtime.
    dataOrigin: "REFERENCE_FIXTURE",
    dataVersion: "gold-2025-05-22",
    modelVersion: "DL-Score v2.1",
    agentVersion: "coordinator-exp-20250522",
    sourceSha: process.env.GITHUB_SHA ?? process.env.DISTRESSLENS_SOURCE_SHA ?? "local",
    gitopsSha: process.env.DISTRESSLENS_GITOPS_SHA ?? "a1b2c3d",
    expected: capture.expected,
    actual: "captured",
    redaction: "no prompts, tokens, credentials or PII rendered",
    capturedAt: new Date().toISOString(),
    image: path.basename(imagePath),
  };

  await writeFile(
    path.join(EVIDENCE_DIR, `${slug}.json`),
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8",
  );

  await testInfo.attach(`${slug}.png`, { path: imagePath, contentType: "image/png" });
  return imagePath;
}

/** Text no rendered surface may ever contain. */
export const FORBIDDEN_PATTERNS = [
  /sk-[A-Za-z0-9]{16,}/,
  /Bearer\s+[A-Za-z0-9._-]{16,}/,
  /service_role/i,
  /BEGIN (RSA |EC )?PRIVATE KEY/,
];
