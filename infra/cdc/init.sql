CREATE USER cdc_reader WITH REPLICATION LOGIN PASSWORD 'cdc_reader';
CREATE TABLE IF NOT EXISTS public.financial_events (
    event_id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    known_from_ts TIMESTAMPTZ NOT NULL,
    close_price DECIMAL(18,0) NOT NULL,
    created_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT CONNECT ON DATABASE financial_distress_cdc TO cdc_reader;
GRANT USAGE ON SCHEMA public TO cdc_reader;
GRANT SELECT ON TABLE public.financial_events TO cdc_reader;
ALTER TABLE public.financial_events REPLICA IDENTITY FULL;
CREATE PUBLICATION financial_distress_cdc_publication FOR TABLE public.financial_events;
