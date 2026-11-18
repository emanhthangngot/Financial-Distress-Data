# Deployment Diagram — Draft

Working draft for the README's high-level deployment diagram, laid out in the same
orientation as `images/architecture/reference-recsys-mlops-overview.png`: actors on
the left, one cluster boundary, namespace boxes inside, data flowing left to right.

Every box is a **deployable unit**. Libraries (Feast SDK, OpenTelemetry SDK) and
formats (Iceberg, Parquet) never get a box — they appear as edge labels.

---

## 1. Full system

```mermaid
flowchart LR
  User(["👤 End user"])
  Dev(["👤 Developer"])
  TF["Terraform"]
  CF["Cloudflare DNS"]
  GH["GitHub"]
  AR["GCP Artifact Registry"]

  subgraph K8S["☸ GKE cluster — 48 vCPU, asia-southeast1-b"]

    subgraph NSING["ns: ingress"]
      NGINX["NGINX Ingress"]
      CERT["cert-manager"]
    end

    subgraph NSWEB["ns: web"]
      WEB["web app<br/>product + chat UI + registry UI"]
    end

    subgraph NSDF["ns: dataflow"]
      GEN["Data Generator"]
      PGSRC["PostgreSQL<br/>source system"]
      DBZ["Debezium<br/>Kafka Connect"]
      KAFKA["Kafka"]
      FLINK["Apache Flink"]
      MINIO["MinIO"]
      ICEB["Iceberg REST Catalog"]
      SPARK["Apache Spark"]
      PGOFF["PostgreSQL<br/>Feast offline store"]
      REDIS["Redis<br/>Feast online store"]
    end

    subgraph NSANA["ns: analytic"]
      TRINO["Trino"]
      SUPER["Superset"]
    end

    subgraph NSGOV["ns: governance"]
      AIRFLOW["Airflow"]
      DHUB["DataHub GMS + Frontend"]
      ES["Elasticsearch"]
    end

    subgraph NSKF["ns: kubeflow"]
      KFP["Kubeflow Pipelines"]
      RAY["Ray cluster"]
    end

    subgraph NSTRK["ns: tracking"]
      MLF["MLflow"]
    end

    subgraph NSKS["ns: kserve"]
      TRITONC["Triton — champion"]
      TRITOND["Triton — candidate"]
      VLLM["vLLM / llm-d"]
    end

    subgraph NSAPI["ns: api-serving"]
      FAPI["feature-api"]
      DAPI["drift-api"]
      FMCP["feature-mcp"]
      DMCP["drift-mcp"]
    end

    subgraph NSAG["ns: agents"]
      AGW["agentgateway"]
      ACOORD["coordinator-agent"]
      AFEAT["feature-agent"]
      ADRIFT["drift-agent"]
      AREG["agent registry"]
    end

    subgraph NSRO["ns: rollouts"]
      ROLL["Argo Rollouts"]
    end

    subgraph NSCI["ns: ci"]
      JENK["Jenkins"]
      ACD["Argo CD"]
    end

    subgraph NSSEC["ns: security"]
      VAULT["Vault"]
      ESO["External Secrets Operator"]
    end

    subgraph NSMESH["ns: istio-system"]
      ISTIOD["istiod"]
      KIALI["Kiali"]
    end

    subgraph NSOBS["ns: observability"]
      PROM["Prometheus"]
      LOKI["Loki"]
      JAEG["Jaeger"]
      OTEL["OTel Collector"]
      PUSHGW["PushGateway"]
      GRAF["Grafana"]
    end
  end

  %% ---- Flow 1: end user (green) ----
  User -- "① HTTPS request" --> NGINX
  NGINX -- "② routed request" --> WEB
  WEB -- "③ prompt" --> AGW
  AGW -- "④ agent invocation" --> ACOORD
  ACOORD -- "⑤ MCP tool call" --> FMCP
  FMCP -- "⑥ entity_id → features" --> REDIS
  ACOORD -- "⑦ completion request" --> VLLM
  VLLM -- "⑧ answer" --> WEB

  %% ---- Flow 2: data (blue) ----
  GEN -- "① company master + statements" --> PGSRC
  GEN -- "② statement snapshots (parquet)" --> MINIO
  GEN -- "③ price ticks" --> KAFKA
  PGSRC -- "④ WAL" --> DBZ
  DBZ -- "⑤ CDC events (before/after)" --> KAFKA
  KAFKA -- "⑥ raw events → bronze" --> MINIO
  MINIO -- "⑦ bronze → silver/gold (Iceberg)" --> SPARK
  ICEB -. "table metadata" .- MINIO
  SPARK -- "⑧ batch features" --> PGOFF
  KAFKA -- "⑨ ticks + CDC" --> FLINK
  FLINK -- "⑩ fresh online features" --> REDIS
  FLINK -- "⑪ stream features" --> PGOFF
  PGOFF -- "⑫ Feast materialization" --> REDIS
  MINIO -- "⑬ gold tables" --> TRINO
  TRINO -- "⑭ SQL result sets" --> SUPER

  %% ---- Flow 3: ML training (orange) ----
  AIRFLOW -- "① trigger pipeline" --> KFP
  PGOFF -- "② point-in-time training set" --> KFP
  KFP -- "③ distributed train job" --> RAY
  RAY -- "④ model + params + metrics" --> MLF
  MLF -- "⑤ model tagged production" --> TRITOND
  ROLL -- "⑥ 10% → 25% → 50%" --> TRITONC
  FAPI -- "⑦ inference request" --> TRITONC

  %% ---- Flow 4: developer / CI-CD (purple) ----
  Dev -- "① git push" --> GH
  GH -- "② webhook" --> JENK
  JENK -- "③ image digest" --> AR
  JENK -- "④ bump digest commit" --> GH
  GH -- "⑤ desired state" --> ACD
  ACD -- "⑥ reconcile" --> K8S
  Dev -- "IaC apply" --> TF
  TF -- "provisions" --> K8S
  CF -- "DNS-01 challenge" --> CERT

  %% ---- Orchestration (grey, no numbering) ----
  AIRFLOW -. "build tables DAG" .-> SPARK
  AIRFLOW -. "materialization DAG" .-> PGOFF
  AIRFLOW -. "drift DAG" .-> DAPI
  DAPI -. "PSI" .-> PUSHGW
  AIRFLOW -. "lineage (Kafka emitter)" .-> DHUB
  DHUB -. "search index" .-> ES

  %% ---- Observability + platform (dashed, non-primary) ----
  NSAPI -. "metrics / logs / traces" .-> OTEL
  NSAG -. "metrics / logs / traces" .-> OTEL
  OTEL -. "spans" .-> JAEG
  PROM -. "scrape" .-> NSAPI
  LOKI -. "logs" .-> GRAF
  PROM -. "metrics" .-> GRAF
  JAEG -. "traces" .-> GRAF
  PROM -. "analysis gate" .-> ROLL
  VAULT -. "secrets" .-> ESO
  ESO -. "k8s Secrets" .-> NSAPI
  ISTIOD -. "mTLS + AuthorizationPolicy, mesh-wide" .-> K8S
  KIALI -. "service graph" .-> ISTIOD

  classDef userFlow stroke:#2e7d32,stroke-width:2px
  classDef dataFlow stroke:#1565c0,stroke-width:2px
  classDef mlFlow stroke:#ef6c00,stroke-width:2px
  classDef ciFlow stroke:#6a1b9a,stroke-width:2px
```

---

## 2. `ns: dataflow` in detail — the hybrid ingestion design

Two lanes converge on the Feast stores, exactly as the reference arranges them:
batch along the top, event stream along the bottom, offline store above online store.

**This diverges from the reference deliberately.** The reference routes *all*
streaming through Postgres and Debezium because it simulates an e-commerce app whose
source code the data team cannot modify. This project has two genuinely different
kinds of data and routes each the way its nature demands.

```mermaid
flowchart LR
  subgraph LANE_BATCH["LÀN TRÊN — batch + state"]
    direction LR
    GEN1["Data Generator"]
    PGSRC["PostgreSQL<br/>company master + financial statements"]
    DBZ["Debezium CDC<br/>Kafka Connect"]
    MINIO["MinIO<br/>object storage"]
    BRONZE[("Bronze tables")]
    SILVER[("Silver / Gold tables")]
    OBT[("Analytic OBT")]
    SPARK["Apache Spark<br/>batch feature engineering"]
  end

  subgraph LANE_STREAM["LÀN DƯỚI — event stream"]
    direction LR
    GEN2["Data Generator"]
    KAFKA["Kafka"]
    K2B["kafka-to-bronze<br/>consumer"]
    FLINK["Apache Flink<br/>realtime feature engineering"]
  end

  subgraph FEAST["Feast stores"]
    direction TB
    PGOFF["PostgreSQL<br/>Feast OFFLINE store"]
    REDIS["Redis<br/>Feast ONLINE store"]
  end

  GEN1 -- "① company master + statements" --> PGSRC
  GEN1 -- "② statement snapshots (parquet)" --> MINIO
  PGSRC -- "③ WAL" --> DBZ
  DBZ -- "④ CDC events — before/after, catches restatements" --> KAFKA

  GEN2 -- "⑤ price ticks — topic financial.price_events" --> KAFKA

  KAFKA -- "⑥ raw events" --> K2B
  K2B -- "⑦ partitioned by event_date / event_hour" --> BRONZE
  MINIO -- "⑧ raw files" --> BRONZE
  BRONZE -- "⑨ cleaned, deduped" --> SILVER
  SILVER -- "⑩ run SQL (Trino)" --> OBT
  SILVER -- "⑪ partitioned reads" --> SPARK
  SPARK -- "⑫ batch features" --> PGOFF

  KAFKA -- "⑬ ticks ⋈ latest statement state" --> FLINK
  FLINK -- "⑭ fresh online features" --> REDIS
  FLINK -- "⑮ stream features" --> PGOFF
  PGOFF -- "⑯ Feast materialization (incremental)" --> REDIS
```

### Why price ticks skip Postgres

| | Price ticks | Financial statements |
|---|---|---|
| Nature | **Event** — happened, immutable | **State** — a row that gets corrected |
| Can it change? | No. Nobody revises yesterday's 10:31 quote | Yes. Restatements, late filings, corrections |
| Consistency need | None — no OLTP state to agree with | Must match committed DB state exactly |
| Route | Producer → Kafka directly | Postgres → CDC → Kafka |
| Verified in code | `src/generator/streaming.py:59` → topic `financial.price_events` | — |

Sending ticks through Postgres purely to have Debezium read them back out adds a
deployable unit and latency while solving nothing. Conversely, publishing statement
changes straight to Kafka would reintroduce the **dual-write problem**: a commit that
succeeds while the publish fails leaves the stream missing an event, and no
transaction spans both systems to prevent it. CDC derives the event *from* the
commit, so the two cannot diverge.

### Why the restatement path matters beyond the diagram

When a revised Q3 filing arrives, Debezium emits an `UPDATE` carrying both `before`
and `after`. Any feature already computed from the superseded figures is now wrong
for training — but it was *correct* at the time it was known. That is exactly the
condition the point-in-time leakage guard (novel idea #2) exists to detect, and it
arises naturally here rather than being contrived.

---

## 3. What is deliberately **not** drawn

| Omitted | Reason |
|---|---|
| Feast SDK | A library, not a deployable unit — the rubric names this exact trap. Feast appears as the edge label on materialization |
| Iceberg | A table format. The **Iceberg REST Catalog** is the deployable unit |
| OpenTelemetry SDK | Embedded in each service; only the **Collector** is deployed |
| MCP | A protocol — an edge label between agent and MCP server |
| Helm / kubectl | Tools that run and exit |
| `write views, carts, purchases` (reference has it) | The reference's serving app writes user events back into the source DB, closing a behavioural loop. This project has no such loop — an analyst UI does not generate financial statements. Copying that arrow would leave a flow with no data to name |

---

## 4. Checklist against the grading criteria

- [ ] Every main component is a deployable unit
- [ ] Arrow direction follows data movement; label states **what data**, not a verb
- [ ] Call-only edges (Airflow → Kubeflow API) still drawn as arrows
- [ ] Every arrow numbered and described
- [ ] Four user flows in four colours, each numbered independently from ①
- [ ] Dashed arrows reserved for non-primary flows (observability, secrets, mesh)
- [ ] Cluster boundary drawn, so in-cluster vs out-of-cluster is unambiguous
- [ ] Diagram matches the running system at capture time, not the plan

## Open questions

- `dags/03_collect_market_price_api.py` exposes only `_collect()`; the write target
  is not visible in that file. Confirm whether it publishes to Kafka or writes to
  Postgres before finalising arrow ⑤ — the diagram must match the code.
- Whether the analyst UI should log predictions back to Postgres. If yes, that adds
  a genuine return edge; if no, the diagram stays one-directional as drawn.
