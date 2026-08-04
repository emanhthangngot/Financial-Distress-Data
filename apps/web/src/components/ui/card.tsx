import type { ReactNode } from "react";

/**
 * The single card surface. Every panel on the product uses it, so card padding,
 * radius and border live in one place instead of drifting per section.
 *
 * Cards are separated from the canvas by a hairline plus the faintest lift —
 * stacking heavier shadows is what turns a dense analytics page into mush.
 */

export function Card({
  children,
  className = "",
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
}) {
  return (
    <Tag
      // `min-w-0` so a card that lands in a grid or flex track can shrink below
      // its content: without it, a wide table inside an `overflow-x-auto`
      // wrapper still widens the page instead of scrolling inside itself.
      className={`min-w-0 rounded-lg border border-line-hairline bg-paper-0 shadow-(--shadow-card) ${className}`}
    >
      {children}
    </Tag>
  );
}

/**
 * Card header. `action` is the trailing slot for a filter, a link or a menu;
 * `description` carries the one line that keeps a chart from needing a caption.
 */
export function CardHeader({
  title,
  description,
  action,
  id,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  /** Set when the card body is labelled by this heading, e.g. a chart region. */
  id?: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line-hairline px-5 py-4">
      <div className="min-w-0">
        <h2 id={id} className="text-[18px]">
          {title}
        </h2>
        {description !== undefined ? (
          <p className="mt-1 text-[13px] text-text-muted">{description}</p>
        ) : null}
      </div>
      {action !== undefined ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function CardBody({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`min-w-0 px-5 py-4 ${className}`}>{children}</div>;
}

export function CardFooter({ children }: { children: ReactNode }) {
  return (
    <div className="border-t border-line-hairline px-5 py-3 text-[13px] text-text-muted">
      {children}
    </div>
  );
}
