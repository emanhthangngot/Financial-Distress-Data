/**
 * The DistressLens mark: a lens ring over a falling bar series. It reads as an
 * instrument dial rather than a generic app glyph, which is the one place the
 * "archival instrument panel" direction is allowed to be literal.
 *
 * The mark is two-tone, so it takes the surface it sits on explicitly. Deriving
 * both tones from `currentColor` would render a white tile with white strokes
 * on the navy rail — invisible.
 */

export type BrandTone = "on-paper" | "on-ink";

const TILE_FILL: Record<BrandTone, string> = {
  "on-paper": "var(--color-ink-900)",
  "on-ink": "var(--color-paper-0)",
};

const GLYPH_STROKE: Record<BrandTone, string> = {
  "on-paper": "var(--color-paper-0)",
  "on-ink": "var(--color-ink-900)",
};

export function BrandMark({
  size = 32,
  tone = "on-paper",
}: {
  size?: number;
  tone?: BrandTone;
}) {
  const stroke = GLYPH_STROKE[tone];

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <rect width="32" height="32" rx="7" fill={TILE_FILL[tone]} />
      <circle cx="14.5" cy="14.5" r="7.5" stroke={stroke} strokeWidth="1.8" />
      <path d="M20 20.5 25 25.5" stroke={stroke} strokeWidth="2.2" strokeLinecap="round" />
      <path
        d="M11 17.5v-3M14.5 17.5v-5.5M18 17.5v-2"
        stroke={stroke}
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function BrandLockup({ suffix }: { suffix?: string }) {
  return (
    <span className="flex items-center gap-2.5 text-paper-0">
      <BrandMark tone="on-ink" />
      <span className="text-[17px] font-bold tracking-tight">
        DistressLens
        {suffix !== undefined ? (
          <span className="ml-1.5 font-medium text-paper-2">{suffix}</span>
        ) : null}
      </span>
    </span>
  );
}
