# 01 Data Generator — Stage 1

## Objective

Stage 1 collects real Vietnamese listed-company data where available and uses deterministic fixtures only for tests or smoke runs. The design covers both offline/API batch data and Kafka-first streaming data.

## Scope

In scope:

- company master data
- quarterly financial statements
- daily market prices
- streaming price, news, and alert events
- rule-based `distress_labels`

Out of scope:

- Phase 2 drift simulation
- ML training and model scoring
- AWS S3, Glue, Athena, RDS, EMR, MSK, SageMaker, Kubernetes

## Timestamp Conventions

- `event_timestamp`: when the source business event happened.
- `created_ts`: when the source or local normalized record was created.
- `ingest_ts`: when the record entered Bronze.
- `report_release_date`: when a financial statement became visible for point-in-time joins.

Deduplication uses business keys plus latest `created_ts`. Feature and OBT joins use `event_timestamp` or `report_release_date` to avoid future-data leakage.

## Offline/API Datasets

### companies

Grain: one row per listed company ticker.

Required columns: `ticker`, `company_name`, `exchange`, `created_ts`.

Optional columns: `industry`, `sector`, `listing_date`, `delisted_flag`, `company_size`, `source_system`, `source_url`, `ingest_run_id`, `raw_payload_hash`.

### financial_statements

Grain: one row per ticker per report period.

Required columns: `ticker`, `report_period`, `fiscal_year`, `fiscal_quarter`, `total_assets`, `total_liabilities`, `equity`, `created_ts`.

Optional columns: `current_assets`, `current_liabilities`, `revenue`, `ebit`, `interest_expense`, `net_income`, `operating_cash_flow`, `retained_earnings`, `report_release_date`, `event_timestamp`, `schema_version`, `source_system`, `source_url`, `raw_payload_hash`.

### market_prices_daily

Grain: one row per ticker per trading date.

Required columns: `ticker`, `trading_date`, `close_price`, `volume`, `created_ts`.

Optional columns: `open_price`, `high_price`, `low_price`, `market_cap`, `shares_outstanding`, `event_timestamp`, `source_system`, `source_url`, `raw_payload_hash`.

### distress_labels

Grain: one row per ticker per report period.

Columns: `ticker`, `report_period`, `event_timestamp`, `created_ts`, `distress_label`, `distress_reason`, `z_score`, `rule_version`.

`distress_labels` is derived locally from Silver/Gold financial statement fields before building `obt_company_quarter_risk`.

Rule version: `v1`.

Altman Z double-prime:

```text
Z'' =
  6.56 * (working_capital / total_assets)
+ 3.26 * (retained_earnings / total_assets)
+ 6.72 * (ebit / total_assets)
+ 1.05 * (equity / total_liabilities)
```

Warning rules:

- `debt_to_asset > 0.8`
- `current_ratio < 1.0`
- `net_income < 0` for two consecutive quarters
- `equity < 0`
- `ebit_interest_coverage < 1.0`

Label policy:

- `distress_label = 1` if `z_score < 1.1` or at least two warning rules are true.
- `distress_label = 0` if `z_score > 2.6` and fewer than two warning rules are true.
- If `z_score` is null, still apply warning rules. If fewer than two warning rules are true, set `distress_label = NULL` and `distress_reason = insufficient_data`.
- If `1.1 <= z_score <= 2.6` and fewer than two warning rules are true, set `distress_label = 0` and include `gray_zone_monitor` in `distress_reason`.

## Streaming Datasets

Kafka topics:

- `financial.price_events`
- `financial.news_events`
- `financial.alert_events`

Each topic uses three partitions for Stage 1 demo scale. The consumer flushes every 60 seconds or 1000 records, whichever comes first.

Bronze streaming path:

```text
s3a://financial-distress-lake/bronze/kafka/{topic}/event_date=YYYY-MM-DD/event_hour=HH/batch_id=.../
```

The Bronze-to-Silver streaming step reads all files in a time window, deduplicates by `event_id`, and writes compact Silver partitions.

## Realistic Data Challenges

Stage 1 fixtures and collectors must cover:

- skewed industry distribution
- high-cardinality tickers and event IDs
- missing `retained_earnings`, `interest_expense`, or `market_cap`
- duplicate financial statements and Kafka events
- late arrivals where `created_ts > event_timestamp`
- outliers such as negative equity and large price drops
- bursty market-open/market-close traffic

## Volume Strategy

Approximate batch volume:

| Dataset | Calculation | Records |
|---|---:|---:|
| `financial_statements` | 300 tickers * 32 quarters | ~9,600 |
| `market_prices_daily` | 300 tickers * ~2,000 trading days | ~600,000 |
| `price_events` | historical replay or polling stream | primary source for 20M target |

The `>=20M` record target is reached mainly through high-volume `price_events` replay when source access and local machine resources allow. CI and smoke runs use small deterministic fixtures.
