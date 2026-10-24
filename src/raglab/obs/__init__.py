"""Observability (S9; docs/OBSERVABILITY.md): the OpenTelemetry tracer behind the Tracer port, the
allowlist every exported span passes through, the GenAI names pinned by commit, and the traced
embedder. The only package that imports opentelemetry (scripts/check_architecture.py, rule 7);
raglab.obs.otel holds those imports, and the other modules import nothing from it, so the names
and the traced embedder load without the SDK."""
