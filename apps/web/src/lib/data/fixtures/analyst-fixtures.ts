import type {
  AlertItem,
  CompanyRiskRow,
  RiskBandSummary,
  SectorRisk,
} from "@distresslens/contracts";

/**
 * Deterministic analyst-overview fixtures matching the UI-APPROVED-01
 * reference. These are sample values for layout and state proof, never live
 * financial data — every surface renders them under a REFERENCE_FIXTURE badge.
 */

export const FIXTURE_BAND_SUMMARIES: readonly RiskBandSummary[] = [
  { band: "HIGH", companyCount: 6, changeVsPriorWeek: 2 },
  { band: "WATCH", companyCount: 14, changeVsPriorWeek: 1 },
  { band: "STABLE", companyCount: 20, changeVsPriorWeek: -3 },
];

export const FIXTURE_ATTENTION_ROWS: readonly CompanyRiskRow[] = [
  {
    ticker: "NVL",
    name: "CTCP Tập đoàn Đầu tư Địa ốc No Va",
    sector: "Bất động sản",
    exchange: "HOSE",
    distressProbability: 78.6,
    band: "HIGH",
    trend: "UP_STRONG",
    dataThrough: "2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
  {
    ticker: "HPG",
    name: "CTCP Tập đoàn Hòa Phát",
    sector: "Thép",
    exchange: "HOSE",
    distressProbability: 61.3,
    band: "HIGH",
    trend: "UP",
    dataThrough: "2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
  {
    ticker: "PDR",
    name: "CTCP Phát triển Bất động sản Phát Đạt",
    sector: "Bất động sản",
    exchange: "HOSE",
    distressProbability: 59.2,
    band: "HIGH",
    trend: "UP",
    dataThrough: "2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
  {
    ticker: "DIG",
    name: "Tổng CTCP Đầu tư Phát triển Xây dựng",
    sector: "Xây dựng & Vật liệu",
    exchange: "HOSE",
    distressProbability: 54.1,
    band: "WATCH",
    trend: "FLAT",
    dataThrough: "2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
  {
    ticker: "VND",
    name: "CTCP Chứng khoán VNDIRECT",
    sector: "Dịch vụ tài chính",
    exchange: "HOSE",
    distressProbability: 48.7,
    band: "WATCH",
    trend: "UP",
    dataThrough: "2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
  {
    ticker: "DCM",
    name: "CTCP Phân bón Dầu khí Cà Mau",
    sector: "Hóa chất",
    exchange: "HOSE",
    distressProbability: 42.3,
    band: "WATCH",
    trend: "FLAT",
    dataThrough: "2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
  {
    ticker: "VIX",
    name: "CTCP Chứng khoán VIX",
    sector: "Dịch vụ tài chính",
    exchange: "HOSE",
    distressProbability: 38.6,
    band: "WATCH",
    trend: "DOWN",
    dataThrough: "2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
  {
    ticker: "FRT",
    name: "CTCP Bán lẻ Kỹ thuật số FPT",
    sector: "Bán lẻ",
    exchange: "HOSE",
    distressProbability: 35.1,
    band: "STABLE",
    trend: "DOWN",
    dataThrough: "2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
];

export const FIXTURE_ATTENTION_TOTAL = 40;

export const FIXTURE_ALERTS: readonly AlertItem[] = [
  {
    id: "alert-0831",
    ticker: "NVL",
    band: "HIGH",
    headline: "NVL – Nguy cơ cao tăng",
    detail: "Xác suất distress tăng từ 72.4% lên 78.6%",
    occurredAt: "2025-05-23T08:31:00+07:00",
  },
  {
    id: "alert-0752",
    ticker: "HPG",
    band: "WATCH",
    headline: "HPG – Xu hướng rủi ro tăng",
    detail: "Chỉ báo đòn bẩy tài chính suy yếu",
    occurredAt: "2025-05-23T07:52:00+07:00",
  },
  {
    id: "alert-0645",
    ticker: "PDR",
    band: "WATCH",
    headline: "PDR – Dòng tiền từ HĐKD âm",
    detail: "Dòng tiền thuần Q1/2025 là -386 tỷ VND",
    occurredAt: "2025-05-23T06:45:00+07:00",
  },
  {
    id: "alert-0610",
    ticker: "DCM",
    band: "WATCH",
    headline: "DCM – Biên lợi nhuận giảm",
    detail: "Biên LNG Q1/2025 giảm xuống 12.1%",
    occurredAt: "2025-05-23T06:10:00+07:00",
  },
  {
    id: "alert-0528",
    ticker: "FRT",
    band: "STABLE",
    headline: "FRT – Tín hiệu tích cực",
    detail: "Xác suất distress giảm xuống 35.1%",
    occurredAt: "2025-05-23T05:28:00+07:00",
  },
];

export const FIXTURE_SECTOR_RISKS: readonly SectorRisk[] = [
  { sector: "Bất động sản", averageDistressProbability: 62.7, changeOver7Days: 4.6 },
  { sector: "Xây dựng & Vật liệu", averageDistressProbability: 54.3, changeOver7Days: 2.8 },
  { sector: "Dịch vụ tài chính", averageDistressProbability: 41.8, changeOver7Days: 1.7 },
  { sector: "Hóa chất", averageDistressProbability: 38.6, changeOver7Days: 0 },
  { sector: "Thép", averageDistressProbability: 32.1, changeOver7Days: -1.6 },
  { sector: "Bán lẻ", averageDistressProbability: 28.4, changeOver7Days: -2.3 },
  { sector: "Thực phẩm & Đồ uống", averageDistressProbability: 22.7, changeOver7Days: -1.1 },
  { sector: "Điện, nước & xăng dầu khí đốt", averageDistressProbability: 18.9, changeOver7Days: -0.8 },
];

export const FIXTURE_MARKET_AVERAGE = 34.2;

export const FIXTURE_METHOD_NOTE =
  "Xác suất distress được ước tính bởi mô hình DL-Score v2.1 dựa trên kết hợp 45 chỉ tiêu tài chính, thanh khoản và phi tài chính. Dữ liệu được cập nhật hàng ngày.";
