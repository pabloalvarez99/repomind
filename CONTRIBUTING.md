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

Add or update fixture expectations with behavior changes. Do not weaken an expectation only to
make a score green. Do not add arbitrary filesystem paths to the HTTP contract, follow
symlinks, execute fixture code, or introduce network access in default tests.
