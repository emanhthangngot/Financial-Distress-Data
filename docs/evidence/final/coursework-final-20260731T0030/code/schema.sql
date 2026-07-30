CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE bronze.companies (
    ticker VARCHAR PRIMARY KEY,
    company_name VARCHAR NOT NULL,
    exchange VARCHAR NOT NULL,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE bronze.financial_statements (
    ticker VARCHAR NOT NULL,
    report_period VARCHAR NOT NULL,
    total_assets DOUBLE,
    total_liabilities DOUBLE,
    event_timestamp TIMESTAMP,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE bronze.market_prices_daily (
    ticker VARCHAR NOT NULL,
    trading_date DATE NOT NULL,
    close_price DOUBLE,
    event_timestamp TIMESTAMP,
    created_ts TIMESTAMP NOT NULL
);

CREATE TABLE silver.companies (
    ticker VARCHAR PRIMARY KEY,
    company_name VARCHAR NOT NULL,
    exchange VARCHAR NOT NULL,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE silver.financial_statements (
    ticker VARCHAR NOT NULL,
    report_period VARCHAR NOT NULL,
    total_assets DOUBLE,
    total_liabilities DOUBLE,
    event_timestamp TIMESTAMP NOT NULL,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE silver.market_prices_daily (
    ticker VARCHAR NOT NULL,
    trading_date DATE NOT NULL,
    close_price DOUBLE,
    event_timestamp TIMESTAMP NOT NULL,
    created_ts TIMESTAMP NOT NULL
);

CREATE TABLE gold.dim_company (
    company_version_key VARCHAR PRIMARY KEY,
    company_key VARCHAR NOT NULL,
    ticker VARCHAR NOT NULL,
    company_name VARCHAR NOT NULL,
    valid_from_ts TIMESTAMP NOT NULL,
    valid_to_ts TIMESTAMP,
    is_current BOOLEAN NOT NULL
);
CREATE TABLE gold.dim_date (
    date_key INTEGER PRIMARY KEY,
    calendar_date DATE UNIQUE NOT NULL
);
CREATE TABLE gold.fact_financial_statement (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    report_period VARCHAR NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE gold.fact_market_price (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    close_price DOUBLE,
    event_timestamp TIMESTAMP NOT NULL,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE gold.obt_company_quarter_risk (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    report_period VARCHAR NOT NULL,
    distress_label INTEGER
);
CREATE TABLE gold.feat_company_financial_4q (
    company_key VARCHAR NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE gold.feat_company_market_30d (
    company_key VARCHAR NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE gold.feat_company_news_30d (
    company_key VARCHAR NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    created_ts TIMESTAMP NOT NULL
);
CREATE TABLE gold.feat_company_unified (
    company_key VARCHAR NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    feature_event_timestamp TIMESTAMP NOT NULL,
    created_ts TIMESTAMP NOT NULL,
    CHECK (feature_event_timestamp <= event_timestamp)
);
