"""One-shot builder for data/eval/program_questions.jsonl (committed output)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "eval" / "program_questions.jsonl"


def main() -> None:
    """Write the season program set."""
    rows: list[dict[str, object]] = []

    def add(**kwargs: object) -> None:
        rows.append(kwargs)

    for item in [
        ("easy-create-app", "Where is create_app defined?", "mini", "app/main.py", "create_app"),
        ("easy-health", "Where is health defined?", "mini", "app/main.py", "health"),
        ("easy-greet", "Where is greet defined?", "mini", "app/service.py", "GreetingService.greet"),
        (
            "easy-greeting-service",
            "Where is GreetingService defined?",
            "mini",
            "app/service.py",
            "GreetingService",
        ),
        ("easy-boot", "Where is boot defined?", "mini", "app/main.py", "boot"),
        (
            "easy-init",
            "Where is GreetingService.__init__ defined?",
            "mini",
            "app/service.py",
            "GreetingService.__init__",
        ),
        (
            "easy-run-query",
            "Where is run_query defined?",
            "production_rag",
            "production_rag/query_pipeline.py",
            "run_query",
        ),
        (
            "easy-rrf",
            "Where is reciprocal_rank_fusion defined?",
            "production_rag",
            "production_rag/retrieval/rrf.py",
            "reciprocal_rank_fusion",
        ),
        ("easy-foo", "Where is foo defined?", "mini_js", "src/foo.js", "foo"),
        ("easy-bar", "Where is bar defined?", "mini_js", "src/foo.js", "bar"),
        ("easy-counter", "Where is Counter defined?", "mini_js", "src/util.ts", "Counter"),
        (
            "easy-check-evidence",
            "Where is check_evidence defined?",
            "production_rag",
            "production_rag/generation/guardrails.py",
            "check_evidence",
        ),
    ]:
        add(
            id=item[0],
            question=item[1],
            repo_id=item[2],
            slice="symbol-easy",
            expected_path=item[3],
            expected_symbol=item[4],
        )

    for item in [
        (
            "xf-greeting-method",
            "Which method renders a greeting for a name?",
            "mini",
            "app/service.py",
            "GreetingService.greet",
            "app/main.py",
        ),
        (
            "xf-prefix-store",
            "Which code stores the configured greeting prefix?",
            "mini",
            "app/service.py",
            "GreetingService.__init__",
            "app/main.py",
        ),
        (
            "xf-app-name",
            "Which function returns the application name mini?",
            "mini",
            "app/main.py",
            "create_app",
            "app/service.py",
        ),
        (
            "xf-liveness",
            "Which code returns the fixture process liveness payload?",
            "mini",
            "app/main.py",
            "health",
            "app/service.py",
        ),
        (
            "xf-wire-service",
            "Which function creates the fixture application?",
            "mini",
            "app/main.py",
            "create_app",
            "app/service.py",
        ),
        (
            "xf-boot-start",
            "Which function named boot starts the fixture application?",
            "mini",
            "app/main.py",
            "boot",
            "app/service.py",
        ),
        (
            "xf-service-class-prose",
            "Which class renders deterministic greetings with a configured prefix?",
            "mini",
            "app/service.py",
            "GreetingService",
            "app/main.py",
        ),
        (
            "xf-query-route",
            "Where is the API query route function defined?",
            "production_rag",
            "production_rag/api/routes/query.py",
            "query",
            "production_rag/query_pipeline.py",
        ),
    ]:
        add(
            id=item[0],
            question=item[1],
            repo_id=item[2],
            slice="cross-file",
            expected_path=item[3],
            expected_symbol=item[4],
            mention_path=item[5],
        )

    for item in [
        (
            "rn-create-app",
            "Where did create_app go after the rename?",
            "mini",
            "app/main.py",
            "create_app",
            "app/application.py",
        ),
        (
            "rn-greeting-service",
            "Where did GreetingService go after the rename?",
            "mini",
            "app/service.py",
            "GreetingService",
            "app/greeter.py",
        ),
        (
            "rn-old-path-create",
            "Where did app/application.py go after rename?",
            "mini",
            "app/main.py",
            "create_app",
            "app/application.py",
        ),
        (
            "rn-old-path-greeter",
            "Where did app/greeter.py go after the rename?",
            "mini",
            "app/service.py",
            "GreetingService",
            "app/greeter.py",
        ),
        (
            "rn-create-app-moved",
            "Where has create_app moved to?",
            "mini",
            "app/main.py",
            "create_app",
            "app/application.py",
        ),
    ]:
        add(
            id=item[0],
            question=item[1],
            repo_id=item[2],
            slice="rename/history",
            expected_path=item[3],
            expected_symbol=item[4],
            old_path=item[5],
        )

    for index, question in enumerate(
        [
            "Who won the Antarctic chess championship?",
            "Where is the database migration runner?",
            "Where is must_not_be_indexed defined?",
            "Where is generated_symbol defined?",
            "Where is QuantumDatabaseRouter defined?",
            "How do I deploy to production Kubernetes?",
            "Where is FakePaymentGateway defined?",
            "What is the CEO phone number?",
        ],
        start=1,
    ):
        add(
            id=f"unans-{index}",
            question=question,
            repo_id="mini",
            slice="unanswerable",
            expect_refusal=True,
        )

    for item in [
        (
            "js-foo-prose",
            "Which function is exported as the primary helper in the mini JS fixture?",
            "src/foo.js",
            "foo",
        ),
        (
            "js-bar-prose",
            "Which export is the bar helper in foo.js?",
            "src/foo.js",
            "bar",
        ),
        (
            "js-counter-prose",
            "Which TypeScript class tracks a numeric counter?",
            "src/util.ts",
            "Counter",
        ),
        (
            "js-foo-behavior",
            "Which JavaScript function lives in src/foo.js for the free-path scanner?",
            "src/foo.js",
            "foo",
        ),
        (
            "js-bar-behavior",
            "Where is the bar export defined in the JavaScript fixture?",
            "src/foo.js",
            "bar",
        ),
        (
            "js-counter-type",
            "Which class in util.ts is part of the mini_js catalog?",
            "src/util.ts",
            "Counter",
        ),
    ]:
        add(
            id=item[0],
            question=item[1],
            repo_id="mini_js",
            slice="js-symbol",
            expected_path=item[2],
            expected_symbol=item[3],
        )

    for item in [
        (
            "df-run-query-prose",
            "Where does run_query live as a module-level function?",
            "production_rag/query_pipeline.py",
            "run_query",
        ),
        (
            "df-graph-prose",
            "Where is build_query_graph defined in the graph package?",
            "production_rag/graph/build.py",
            "build_query_graph",
        ),
        (
            "df-rrf-prose",
            "Which function fuses ranked result lists with reciprocal rank fusion?",
            "production_rag/retrieval/rrf.py",
            "reciprocal_rank_fusion",
        ),
        (
            "df-fake-embed",
            "Which embedding provider class is the offline fake for free-path tests?",
            "production_rag/retrieval/embeddings.py",
            "FakeEmbeddingProvider",
        ),
        (
            "df-guard-prose",
            "Which guardrail function checks whether retrieved evidence supports answering?",
            "production_rag/generation/guardrails.py",
            "check_evidence",
        ),
        (
            "df-query-route-prose",
            "Which HTTP handler exposes the query API route for production RAG?",
            "production_rag/api/routes/query.py",
            "query",
        ),
        (
            "df-build-pipeline",
            "Where is build_query_pipeline defined?",
            "production_rag/query_pipeline.py",
            "build_query_pipeline",
        ),
        (
            "df-openai-embed-class",
            "Which embedding provider class talks to OpenAI when configured?",
            "production_rag/retrieval/embeddings.py",
            "OpenAIEmbeddingProvider",
        ),
    ]:
        add(
            id=item[0],
            question=item[1],
            repo_id="production_rag",
            slice="dogfood-locate",
            expected_path=item[2],
            expected_symbol=item[3],
        )

    for item in [
        ("json-service-name", "Where is service_name defined?", "config/settings.json", "service_name"),
        (
            "json-greeting-prefix",
            "Where is greeting_prefix defined?",
            "config/settings.json",
            "greeting_prefix",
        ),
        ("json-feature-flags", "Where is feature_flags defined?", "config/settings.json", "feature_flags"),
        ("json-max-citations", "Where is max_citations defined?", "config/settings.json", "max_citations"),
        (
            "json-service-prose",
            "Which JSON field names the mini fixture service?",
            "config/settings.json",
            "service_name",
        ),
    ]:
        add(
            id=item[0],
            question=item[1],
            repo_id="mini",
            slice="json-field",
            expected_path=item[2],
            expected_symbol=item[3],
        )

    OUT.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    print("n=", len(rows))
    print(Counter(str(row["slice"]) for row in rows))


if __name__ == "__main__":
    main()
