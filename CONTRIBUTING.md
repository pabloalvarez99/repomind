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

Commit the regenerated PNGs and the updated `docs/assets/ui-captures.sha256` in the **same
commit** as the template, stylesheet, or answer-text change that caused them. CI never launches a
browser; it only checks hashes, so a stale capture is caught by `tests/test_capture_assets.py`
rather than by a reviewer squinting at a screenshot. That test fails when a documented image is
missing, when a referenced PNG has no manifest entry, or when committed bytes drift from the
recorded sha256.

```bash
# after python scripts/capture_ui.py, refresh the sidecar from the files it wrote
python - <<'PY'
import hashlib, pathlib
lines = [
    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  docs/assets/{path.name}"
    for path in sorted(pathlib.Path("docs/assets").glob("*.png"))
]
pathlib.Path("docs/assets/ui-captures.sha256").write_text("\n".join(lines) + "\n", newline="\n")
PY
pytest -q tests/test_capture_assets.py
```

Add or update fixture expectations with behavior changes. Do not weaken an expectation only to
make a score green. Do not add arbitrary filesystem paths to the HTTP contract, follow
symlinks, execute fixture code, or introduce network access in default tests.
