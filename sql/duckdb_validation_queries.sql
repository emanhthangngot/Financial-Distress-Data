SELECT COUNT(*) AS total_financial_statement_rows
FROM gold_fact_financial_statement;

SELECT ticker, report_period, COUNT(*) AS cnt
FROM gold_fact_financial_statement
GROUP BY ticker, report_period
HAVING COUNT(*) > 1;

SELECT distress_label, COUNT(*) AS row_count
FROM gold_obt_company_quarter_risk
GROUP BY distress_label;

SELECT COUNT(*) AS total_dim_company_rows
FROM gold_dim_company;

SELECT COUNT(*) AS total_dim_date_rows
FROM gold_dim_date;

SELECT COUNT(*) AS total_news_sentiment_rows
FROM gold_fact_news_sentiment;

SELECT COUNT(*) AS total_market_alert_rows
FROM gold_fact_market_alert;

SELECT COUNT(*) AS total_financial_feature_rows
FROM gold_feat_company_financial_4q;

SELECT COUNT(*) AS total_market_feature_rows
FROM gold_feat_company_market_30d;

SELECT COUNT(*) AS total_news_feature_rows
FROM gold_feat_company_news_30d;

SELECT COUNT(*) AS future_feature_leakage_rows
FROM gold_feat_company_unified
WHERE feature_event_timestamp IS NOT NULL
  AND CAST(feature_event_timestamp AS TIMESTAMP) > CAST(event_timestamp AS TIMESTAMP);

SELECT *
FROM gold_feat_company_unified
LIMIT 20;
