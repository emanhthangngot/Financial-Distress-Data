"use client";

import { Button } from "@/components/ui/button";

/**
 * Export a saved report.
 *
 * Export is the browser's own print-to-PDF: the report is already a complete
 * document carrying its disclaimer, sources and provenance, so rendering it a
 * second time server-side would add a dependency and a second thing to keep in
 * sync with no gain. The button says "Xuất báo cáo (PDF)" because that is
 * exactly what the reader gets.
 */
export function ExportReportButton() {
  return (
    <Button type="button" variant="primary" onClick={() => window.print()}>
      Xuất báo cáo (PDF)
    </Button>
  );
}
