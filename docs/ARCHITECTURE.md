# Architecture

The system, its evaluation loop, its delivery path and the stage map, as Mermaid diagrams
(GitHub renders them). These diagrams are the progress map: every stage PR moves its nodes in
diagram 4 from `todo` to `wip` to `done`, and `tests/unit/test_diagram.py` checks that every node a
stage plan names exists here and that each node has exactly one status.

Colours in diagrams 1 to 3 show the phase that builds each part: blue P1 lab core, green P2
evaluation rigour, amber P3 production practices, grey dashed P4 documented only (the path to
production, not built). In diagram 4, grey is todo, amber is in progress, green is done.

### 1. Full system (runtime)

```mermaid
flowchart LR
  subgraph Clients
    UI[Web UI]:::p1
    CLI[CLI]:::p1
    PG[Pages playground<br/>reads published runs]:::p1
  end
  subgraph API[FastAPI service]
    LIM[Demo controls<br/>rate, budget, kill switch]:::p3
    GIN[Input guards<br/>limits, injection, topic, PII]:::p2
    PIPE[Pipeline]:::p1
    GOUT[Output guards<br/>citations, grounding, PII]:::p2
  end
  subgraph Ingest[Ingestion, offline]
    DOCS[(Corpus<br/>policy, later handbook)]:::p1
    PARSE[Parse text, PDF, OCR]:::p1
    CHUNK[Chunk + metadata<br/>doc, version, page, tenant]:::p1
    SCAN[Instruction scan on ingest]:::p2
  end
  subgraph Retrieval
    EMB[Embedder port<br/>ONNX local, hosted]:::p1
    VS[(VectorStore port<br/>in-memory, Qdrant)]:::p1
    BM[BM25 hybrid]:::p1
    TEN[Tenant filter, fail closed]:::p1
  end
  subgraph Models[Adapters, the only vendor imports]
    FAKE[Fake / perf stub]:::p1
    OAI[OpenAI-compatible<br/>Ollama, OpenAI, Groq, vLLM]:::p1
    ANT[Anthropic]:::p2
    BED[Bedrock, optional]:::p4
  end
  OBS[OTel gen_ai spans<br/>+ redaction]:::p3
  LF[(Langfuse, optional)]:::p3

  UI --> LIM --> GIN --> PIPE
  CLI --> PIPE
  DOCS --> PARSE --> CHUNK --> SCAN --> EMB --> VS
  PIPE --> TEN --> VS
  PIPE --> BM
  PIPE --> Models
  PIPE --> GOUT --> UI
  PIPE -.-> OBS -.-> LF

  classDef p1 fill:#dbeafe,stroke:#1e40af
  classDef p2 fill:#dcfce7,stroke:#166534
  classDef p3 fill:#fef3c7,stroke:#92400e
  classDef p4 fill:#f3f4f6,stroke:#6b7280,stroke-dasharray:4
```

Key: blue P1 lab core, green P2 evaluation rigour, amber P3 production practices, grey dashed
P4 documented only.

### 2. Evaluation and gates (offline)

```mermaid
flowchart LR
  GS[(Golden set v1<br/>retrieval + behaviour<br/>dev / test split)]:::p1 --> CD[check-dataset<br/>consistency gate]:::p1
  CD --> RUN[N-trial runner<br/>budget abort]:::p1
  CFG[config/*.toml<br/>model, embedder, chunker]:::p1 --> RUN
  RUN --> DET[Deterministic metrics<br/>hit, MRR, recall@k,<br/>citations, abstention]:::p1
  RUN --> JDG[Judged metrics<br/>DeepEval + own judge]:::p2
  CAL[(30 blind labels<br/>kappa, threshold)]:::p2 --> JDG
  DET --> REC[(Run record v1<br/>manifest, cases.jsonl, report)]:::p1
  JDG --> REC
  REC --> CMP[compare<br/>paired diff, flipped cases]:::p1
  CMP --> GATE{Gates<br/>pr-fast, eval-on-change,<br/>nightly, weekly, release}:::p2
  REC --> PUB[publish<br/>schema, hashes, privacy]:::p1 --> PG[Playground]:::p1
  RT[Red team + security suites]:::p2 --> GATE
  classDef p1 fill:#dbeafe,stroke:#1e40af
  classDef p2 fill:#dcfce7,stroke:#166534
```

### 3. Delivery and deploy

```mermaid
flowchart LR
  DEV[Branch sN] --> PR[PR] --> FAST[pr-fast<br/>lint, types, tests, privacy,<br/>gitleaks, bandit, semgrep, pip-audit]
  FAST --> REV[Your review + merge]
  REV --> MAIN[main]
  MAIN --> IMG[Build image<br/>trivy, SBOM at release]
  IMG --> ENV{Environment<br/>required reviewers}
  ENV --> HOST[Cheap host<br/>scale to zero, 1 instance]
  HOST --> ZAP[ZAP baseline]
  MAIN --> PAGES[Pages: playground]
  HOST -. path to prod, doc only .-> AWS[AWS: ECS/EKS, Bedrock,<br/>Guardrails, Secrets Manager,<br/>OTel collector]
```

### 4. Phase map (what each phase builds)

```mermaid
flowchart TB
  subgraph P1[P1 Lab core, v0.1]
    S0[S0 Skeleton, hygiene, security CI] --> S1a[S1a Requirements, corpus pack, answer key] --> S1b[S1b Ingestion, chunking, test plan] --> S2[S2 Retrieval, run record, playground v0] --> S3[S3 Generation, local live run, API/UI, local container] --> S3h[S3h Host evaluation spike] --> S4[S4 Golden set, consistency gate]
  end
  subgraph P2[P2 Evaluation rigour, v0.2]
    S4b[S4b Golden set v2, ~120] --> S5[S5 Local judged metrics, token measurement, provider decision] --> S6[S6 Judge calibration] --> S7[S7 Attack, guardrails, red team] --> S8[S8 Gates, causes, suite audit]
  end
  subgraph P3[P3 Production practices, v0.3]
    S9[S9 Observability, perf] --> S10[S10 Real demo, path to prod] --> S11[S11 Teaching playground, system audit, capstone]
  end
  subgraph EXT[Extensions]
    S12[S12 Handbook corpus]
    B[Track B Playwright for Python]
  end
  S4 --> S4b
  S8 --> S9
  S11 --> S12
  S3 -.-> B
  classDef todo fill:#f3f4f6,stroke:#6b7280
  classDef wip fill:#fef3c7,stroke:#92400e
  classDef done fill:#dcfce7,stroke:#166534
  class S0,S1a done
  class S1b,S2,S3,S3h,S4,S4b,S5,S6,S7,S8,S9,S10,S11,S12,B todo
```
