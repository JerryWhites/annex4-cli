# Contributing to annex4-cli

First off, thank you for considering contributing to `annex4-cli`. It's people like you that make open source such a great community.

## Getting Started

- Ensure you have Python 3.11+ and `uv` installed.
- Clone the repository: `git clone https://github.com/JerryWhites/annex4-cli.git`
- Change into the directory: `cd annex4-cli`
- Set up the development environment: `uv sync -e dev`
- Activate the virtual environment: `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
- Install pre-commit hooks: `pre-commit install`

Now you're ready to make changes!

## Running Tests

To run the full test suite:
`pytest`

To run tests with coverage:
`pytest --cov`

## Code Style

We use `ruff` for linting and formatting. The pre-commit hooks will automatically run these tools on your changes. You can also run them manually:

- `ruff check .`
- `ruff format .`

We also use `mypy` for static type checking:
`mypy annex4`

## Proposing a Change

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes, including tests.
4. Ensure all tests pass and the code is formatted correctly.
5. Push your branch and open a pull request.

### Regulation Mapping Changes

If you are proposing a change to the regulation mappings in `annex4/regulation/`, please:
1. Cite the specific Article and paragraph number from the EU AI Act.
2. Provide a link to the relevant section on EUR-Lex.
3. Explain the reasoning for the change in your pull request description.

This helps ensure that all mappings are accurate and traceable to the source text.
