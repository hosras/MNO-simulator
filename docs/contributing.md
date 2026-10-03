# Contributing

## Development setup

```bash
git clone https://github.com/hosras/MNO-simulator.git
cd MNO-simulator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pre-commit ruff
pre-commit install
```

## Before you commit

1. Run ruff:

```bash
ruff check .
ruff format .
```

2. Run tests:

```bash
pytest --run-slow -q
```

3. Regenerate docs (if you touched code or README):

```bash
python generate_readme.py
python generate_evidence.py
```

## Commit message convention

Follow Conventional Commits:

| Prefix | When to use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `test:` | Tests |
| `chore:` | Tooling, deps, config |
| `refactor:` | No behavior change |
| `ci:` | CI/CD changes |

Example: `feat(simulator): add --random-seed CLI flag`

## Pull request checklist

- [ ] Tests pass locally
- [ ] `ruff check .` is clean
- [ ] New code has docstrings and tests
- [ ] Documentation updated
- [ ] Commits follow the convention

## Style guide

- Line length: 100 characters
- Quotes: double quotes
- Imports: sorted by ruff
- Docstrings: Google-style
