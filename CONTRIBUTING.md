# Contributing to macmorpher

First off, thank you for considering contributing to `macmorpher`!

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct.

## How to Contribute

1. Fork the repo and create your branch from `master`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code passes the linting and type checking (Ruff & Mypy).
6. Issue that pull request!

## Setting up for development

1. Clone your fork and enter the directory.
2. Create a virtual environment: `python3 -m venv .venv`
3. Activate the environment: `source .venv/bin/activate`
4. Install dev dependencies: `pip install -e ".[dev]"`
5. Setup pre-commit: `pre-commit install`

## Testing

Run tests using pytest:

```bash
pytest
```

Thank you for contributing!
