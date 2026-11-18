INSTALL httpfs;
LOAD httpfs;

-- DuckDB is a local, single-node inspection engine for DBeaver/reviewer SQL.
-- It is not used as a horizontally scalable serving layer; authoritative
-- governance state stays in MinIO Parquet plus PostgreSQL ops.
SET s3_endpoint='localhost:9000';
-- W14 S-B: credentials are intentionally not set in the SQL template.
-- DuckDB resolves MINIO_ROOT_USER / MINIO_ROOT_PASSWORD from its own
-- env chain (process env, .env, ~/.aws/credentials).
SET s3_use_ssl=false;
SET s3_url_style='path';

CREATE OR REPLACE VIEW gold_fact_financial_statement AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/fact_financial_statement/**/*.parquet');

CREATE OR REPLACE VIEW gold_fact_market_price AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/fact_market_price/**/*.parquet');

CREATE OR REPLACE VIEW gold_fact_market_alert AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/fact_market_alert/**/*.parquet');

CREATE OR REPLACE VIEW gold_dim_company AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/dim_company/**/*.parquet');

CREATE OR REPLACE VIEW gold_dim_date AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/dim_date/**/*.parquet');

CREATE OR REPLACE VIEW gold_fact_news_sentiment AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/fact_news_sentiment/**/*.parquet');

CREATE OR REPLACE VIEW gold_obt_company_quarter_risk AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/obt_company_quarter_risk/**/*.parquet');

CREATE OR REPLACE VIEW gold_feat_company_financial_4q AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/feat_company_financial_4q/**/*.parquet');

CREATE OR REPLACE VIEW gold_feat_company_market_30d AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/feat_company_market_30d/**/*.parquet');

CREATE OR REPLACE VIEW gold_feat_company_news_30d AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/feat_company_news_30d/**/*.parquet');

CREATE OR REPLACE VIEW gold_feat_company_unified AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/feat_company_unified/**/*.parquet');
