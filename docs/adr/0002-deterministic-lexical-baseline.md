# ADR 0002: Deterministic lexical baseline

Status: accepted for v0.1.0.

RepoMind uses exact symbol matching plus token overlap and deterministic tie-breaking. It does
not use embeddings, a hosted LLM, or a model judge. Exact unsplit identifier matches suppress
weaker candidates; zero positive evidence yields a fixed refusal.

The baseline is cheap, inspectable, and reproducible in CI. It cannot claim semantic retrieval
quality, so the evals are described only as fixture navigation/citation regression gates.
