import type {
  CompanyDetail,
  FinancialIndicator,
  ShapDriver,
  SourceRef,
  TrendPoint,
} from "@distresslens/contracts";
import { FIXTURE_ATTENTION_ROWS } from "./analyst-fixtures";
import { LIVE_FIXTURE_PROVENANCE } from "./provenance-fixtures";

/**
 * Company-detail fixtures matching UI-APPROVED-02 (NVL). Reference values only;
 * they carry the REFERENCE_FIXTURE origin through `LIVE_FIXTURE_PROVENANCE`.
 */

const NVL_TREND: readonly TrendPoint[] = [
  { period: "Q1/2022", distressProbability: 62.1, altmanZScore: 0.75 },
  { period: "Q2/2022", distressProbability: 68.4, altmanZScore: 0.98 },
  { period: "Q3/2022", distressProbability: 69.2, altmanZScore: 1.24 },
  { period: "Q4/2022", distressProbability: 70.1, altmanZScore: 1.35 },
  { period: "Q1/2023", distressProbability: 71.8, altmanZScore: 1.12 },
  { period: "Q2/2023", distressProbability: 73.9, altmanZScore: 0.81 },
  { period: "Q3/2023", distressProbability: 74.6, altmanZScore: 0.44 },
  { period: "Q4/2023", distressProbability: 73.2, altmanZScore: 0.12 },
  { period: "Q1/2024", distressProbability: 75.1, altmanZScore: -0.28 },
  { period: "Q2/2024", distressProbability: 75.8, altmanZScore: -0.55 },
  { period: "Q3/2024", distressProbability: 76.9, altmanZScore: -0.92 },
  { period: "Q4/2024", distressProbability: 77.4, altmanZScore: -1.18 },
  { period: "Q1/2025", distressProbability: 78.6, altmanZScore: -1.35 },
];

const NVL_PERIODS = ["Q1/2024", "Q4/2024", "Q1/2025"] as const;

const NVL_INDICATORS: readonly FinancialIndicator[] = [
  { name: "Debt/Asset", unit: "lần", values: [0.72, 0.76, 0.79], trend: "UP" },
  { name: "Current Ratio", unit: "lần", values: [0.85, 0.74, 0.66], trend: "DOWN" },
  { name: "ROA", unit: "%", values: [-1.8, -2.6, -3.1], trend: "DOWN" },
  {
    name: "Operating Cash Flow",
    unit: "tỷ VND",
    values: [-1423, -2105, -2386],
    trend: "DOWN",
  },
];

const NVL_SHAP: readonly ShapDriver[] = [
  { feature: "Debt/Asset (cao hơn)", contribution: 18.7, direction: "INCREASES_RISK" },
  { feature: "Operating Cash Flow (âm)", contribution: 15.6, direction: "INCREASES_RISK" },
  { feature: "Current Ratio (thấp hơn)", contribution: 11.2, direction: "INCREASES_RISK" },
  { feature: "ROA (thấp hơn)", contribution: 9.4, direction: "INCREASES_RISK" },
  { feature: "Quy mô tài sản (ln tổng TS)", contribution: -6.1, direction: "DECREASES_RISK" },
  { feature: "Vốn chủ sở hữu/Tổng tài sản", contribution: -4.3, direction: "DECREASES_RISK" },
  { feature: "Tăng trưởng doanh thu (YoY)", contribution: -3.2, direction: "DECREASES_RISK" },
];

const NVL_SOURCES: readonly SourceRef[] = [
  {
    id: "src-bctc-q1-2025",
    kind: "BCTC",
    title: "Báo cáo tài chính hợp nhất Q1/2025",
    publishedAt: "2025-05-22",
    publisher: "HOSE",
    url: "https://www.hsx.vn",
  },
  {
    id: "src-news-cashflow",
    kind: "NEWS",
    title: "NVL: Dòng tiền kinh doanh âm hơn 2.300 tỷ trong quý 1/2025",
    publishedAt: "2025-05-22",
    publisher: "CafeF",
    url: "https://cafef.vn",
  },
  {
    id: "src-news-bond",
    kind: "NEWS",
    title: "Novaland chậm thanh toán lãi trái phiếu, việc đảo hạn tăng cao",
    publishedAt: "2025-05-21",
    publisher: "VnExpress",
    url: "https://vnexpress.net",
  },
  {
    id: "src-news-sector",
    kind: "NEWS",
    title: "Thị trường BĐS phục hồi chậm, nhiều doanh nghiệp vẫn khó khăn",
    publishedAt: "2025-05-20",
    publisher: "Báo Đầu tư",
    url: "https://baodautu.vn",
  },
];

export const FIXTURE_COMPANY_DETAILS: Readonly<Record<string, CompanyDetail>> = {
  NVL: {
    company: {
      ticker: "NVL",
      name: "CTCP Tập đoàn Đầu tư Địa ốc No Va",
      sector: "Bất động sản",
      exchange: "HOSE",
    },
    distressProbability: 78.6,
    band: "HIGH",
    changeVsPriorRun: 5.6,
    confidence: 72,
    modelVersion: "DL-Score v2.1",
    trend: NVL_TREND,
    indicatorPeriods: [...NVL_PERIODS],
    indicators: NVL_INDICATORS,
    shapDrivers: NVL_SHAP,
    sources: NVL_SOURCES,
    provenance: LIVE_FIXTURE_PROVENANCE,
  },
};

/** Tickers the fixture adapter can resolve to a full detail page. */
export const FIXTURE_DETAIL_TICKERS = Object.keys(FIXTURE_COMPANY_DETAILS);

/** Every ticker the search surface knows about, detail page or not. */
export const FIXTURE_SEARCHABLE_ROWS = FIXTURE_ATTENTION_ROWS;
