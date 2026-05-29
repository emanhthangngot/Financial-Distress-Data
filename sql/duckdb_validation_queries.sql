SELECT COUNT(*) AS total_financial_statement_rows
FROM gold_fact_financial_statement;

SELECT ticker, report_period, COUNT(*) AS cnt
FROM gold_fact_financial_statement
GROUP BY ticker, report_period
HAVING COUNT(*) > 1;

SELECT distress_label, COUNT(*) AS row_count
FROM gold_obt_company_quarter_risk
GROUP BY distress_label;

SELECT *
FROM gold_feat_company_unified
LIMIT 20;
