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

Commit the regenerated PNGs and both refreshed sidecars in the **same commit** as the template,
stylesheet, or answer-text change that caused them. CI never launches a browser; it only checks
hashes, so a stale capture is caught by `tests/test_capture_assets.py` rather than by a reviewer
squinting at a screenshot:

- `docs/assets/ui-captures.sha256` pins the committed PNGs. The test fails when a documented
  image is missing, when a referenced PNG has no manifest entry, or when committed bytes drift.
- `docs/assets/ui-sources.sha256` pins `index.html`, `app.css`, `app.js`, and `capture_ui.py` —
  everything that decides what a screenshot shows. Without it a CSS edit would ship green with
  the old console still on display, because unchanged PNG bytes look identical to correct ones.

So the loop for any console change is: edit, `python scripts/capture_ui.py`, then

```bash
python scripts/hash_ui_assets.py          # rewrites both sidecars; --check reports drift only
pytest -q tests/test_capture_assets.py
```

A failure on `ui-sources.sha256` is not noise: it means the evidence in `docs/assets` no longer
proves the code in this commit. Regenerate rather than editing the hash by hand.

Add or update fixture expectations with behavior changes. Do not weaken an expectation only to
make a score green. Do not add arbitrary filesystem paths to the HTTP contract, follow
symlinks, execute fixture code, or introduce network access in default tests.
