# Contributing

RepoMind's default path must remain deterministic, offline, and free of provider credentials.

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src/repomind
pytest -q
python -m repomind.evals.run
python -m repomind.evals.dogfood
```

UI evidence in `docs/assets` is generated, never hand-edited. Regenerate it after any change to
the console template, stylesheet, or answer text:

```bash
python -m pip install -e ".[docs]"
python -m playwright install chromium
python scripts/capture_ui.py
```

The script asserts each rendered outcome before writing its PNG and prints a sha256 per file;
reruns on an unchanged tree produce identical bytes. Playwright is documentation-only and stays
out of the `dev` extra and out of CI.

Add or update fixture expectations with behavior changes. Do not weaken an expectation only to
make a score green. Do not add arbitrary filesystem paths to the HTTP contract, follow
symlinks, execute fixture code, or introduce network access in default tests.
