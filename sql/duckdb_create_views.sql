INSTALL httpfs;
LOAD httpfs;

SET s3_endpoint='localhost:9000';
SET s3_access_key_id='minioadmin';
SET s3_secret_access_key='minioadmin';
SET s3_use_ssl=false;
SET s3_url_style='path';

CREATE OR REPLACE VIEW gold_fact_financial_statement AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/fact_financial_statement/**/*.parquet');

CREATE OR REPLACE VIEW gold_fact_market_price AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/fact_market_price/**/*.parquet');

CREATE OR REPLACE VIEW gold_obt_company_quarter_risk AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/obt_company_quarter_risk/**/*.parquet');

CREATE OR REPLACE VIEW gold_feat_company_unified AS
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/feat_company_unified/**/*.parquet');
