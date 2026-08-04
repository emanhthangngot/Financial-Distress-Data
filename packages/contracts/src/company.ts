import type { Provenance } from "./provenance";

/**
 * Analyst-surface view models. These are display contracts, not the Gold-layer
 * schema: probabilities arrive already rounded and banded so the browser never
 * re-derives a risk classification the model did not make.
 */

export const RISK_BANDS = ["HIGH", "WATCH", "STABLE"] as const;
export type RiskBand = (typeof RISK_BANDS)[number];

/** Vietnamese labels used across cards, tables and chips. */
export const RISK_BAND_LABELS: Record<RiskBand, string> = {
  HIGH: "Nguy cơ cao",
  WATCH: "Cần theo dõi",
  STABLE: "Ổn định",
};

export const TREND_DIRECTIONS = ["UP_STRONG", "UP", "FLAT", "DOWN", "DOWN_STRONG"] as const;
export type TrendDirection = (typeof TREND_DIRECTIONS)[number];

export const TREND_LABELS: Record<TrendDirection, string> = {
  UP_STRONG: "Tăng mạnh",
  UP: "Tăng",
  FLAT: "Đi ngang",
  DOWN: "Giảm",
  DOWN_STRONG: "Giảm mạnh",
};

export interface CompanyRef {
  ticker: string;
  name: string;
  sector: string;
  exchange: string;
}

export interface CompanyRiskRow extends CompanyRef {
  /** Distress probability as a percentage, 1 decimal place. */
  distressProbability: number;
  band: RiskBand;
  trend: TrendDirection;
  /** ISO date the underlying data covers, not the render time. */
  dataThrough: string;
  modelVersion: string;
}

export interface RiskBandSummary {
  band: RiskBand;
  companyCount: number;
  /** Change in company count versus the prior weekly run. */
  changeVsPriorWeek: number;
}

export interface SectorRisk {
  sector: string;
  averageDistressProbability: number;
  changeOver7Days: number;
}

export interface AlertItem {
  id: string;
  ticker: string;
  band: RiskBand;
  headline: string;
  detail: string;
  occurredAt: string;
}

export interface TrendPoint {
  /** Quarter label, e.g. Q1/2025. */
  period: string;
  distressProbability: number;
  altmanZScore: number;
}

export interface FinancialIndicator {
  name: string;
  unit: string;
  /** Values keyed by period label, ordered by the accompanying `periods` list. */
  values: readonly (number | null)[];
  trend: TrendDirection;
}

export interface ShapDriver {
  feature: string;
  /** Signed contribution to the distress probability, in percentage points. */
  contribution: number;
  direction: "INCREASES_RISK" | "DECREASES_RISK";
}

export const SOURCE_KINDS = ["BCTC", "NEWS", "MARKET", "INTERNAL"] as const;
export type SourceKind = (typeof SOURCE_KINDS)[number];

export interface SourceRef {
  id: string;
  kind: SourceKind;
  title: string;
  publishedAt: string;
  publisher: string;
  url: string | null;
}

export interface CompanyDetail {
  company: CompanyRef;
  distressProbability: number;
  band: RiskBand;
  /** Change in probability versus the prior run, in percentage points. */
  changeVsPriorRun: number;
  /** Model confidence as a percentage. */
  confidence: number;
  modelVersion: string;
  trend: readonly TrendPoint[];
  indicatorPeriods: readonly string[];
  indicators: readonly FinancialIndicator[];
  shapDrivers: readonly ShapDriver[];
  sources: readonly SourceRef[];
  provenance: Provenance;
}

export interface AnalystOverview {
  bandSummaries: readonly RiskBandSummary[];
  attention: readonly CompanyRiskRow[];
  attentionTotal: number;
  alerts: readonly AlertItem[];
  sectorRisks: readonly SectorRisk[];
  marketAverageProbability: number;
  methodNote: string;
  provenance: Provenance;
}

export interface CompanySearchResult {
  rows: readonly CompanyRiskRow[];
  total: number;
  query: string;
  provenance: Provenance;
}

/**
 * Model/version comparison for `/compare`. `baseline` is nullable because a
 * freshly promoted model legitimately has nothing to compare against yet, and
 * that must render as a named state rather than a crash.
 */
export interface ModelComparison {
  ticker: string;
  candidate: ModelComparisonSide;
  baseline: ModelComparisonSide | null;
  provenance: Provenance;
}

export interface ModelComparisonSide {
  modelVersion: string;
  distressProbability: number;
  band: RiskBand;
  confidence: number;
  topDrivers: readonly ShapDriver[];
}

/**
 * Row in the saved-report list. Deliberately not the full `SavedReport`: the
 * list must not carry every company's indicators and sources, and a summary
 * that cannot be expanded into a detail is also a smaller blast radius if the
 * list is ever cached.
 */
export interface SavedReportSummary {
  id: string;
  company: CompanyRef;
  title: string;
  createdAt: string;
  band: RiskBand;
  distressProbability: number;
  /** Set when an admin revoked the report; the row renders as unavailable. */
  revokedAt: string | null;
}

export interface SavedReportList {
  reports: readonly SavedReportSummary[];
  provenance: Provenance;
}

export interface SavedReport {
  id: string;
  ownerId: string;
  company: CompanyRef;
  createdAt: string;
  title: string;
  summary: string;
  detail: CompanyDetail;
  /** Set when an admin revoked the report; readers see a forbidden state. */
  revokedAt: string | null;
}
