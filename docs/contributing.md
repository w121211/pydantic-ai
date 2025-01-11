We'd love you to contribute to PydanticAI!

## Installation and Setup

Clone your fork and cd into the repo directory

```bash
git clone git@github.com:<your username>/pydantic-ai.git
cd pydantic-ai
```

Install `uv` (version 0.4.30 or later) and `pre-commit`

We use pipx here, for other options see:

* [`uv` install docs](https://docs.astral.sh/uv/getting-started/installation/)
* [`pre-commit` install docs](https://pre-commit.com/#install)

To get `pipx` itself, see [these docs](https://pypa.github.io/pipx/)

```bash
pipx install uv pre-commit
```

Install `pydantic-ai`, all dependencies and pre-commit hooks

```bash
make install
```

## Running Tests etc.

We use `make` to manage most commands you'll need to run.

For details on available commands, run:

```bash
make help
```

To run code formatting, linting, static type checks, and tests with coverage report generation, run:

```bash
make
```

## Documentation Changes

To run the documentation page locally, run:

```bash
uv run mkdocs serve
```

## Rules for adding new models to PydanticAI {#new-model-rules}

To avoid an excessive workload for the maintainers of PydanticAI, we can't accept all model contributions, so we're setting the following rules for when we'll accept new models and when we won't. This should hopefully reduce the chances of disappointment and wasted work.

* To add a new model with an extra dependency, that dependency needs > 500k monthly downloads from PyPI consistently over 3 months or more
* To add a new model which uses another models logic internally and has no extra dependencies, that model's GitHub org needs > 20k stars in total
* For any other model that's just a custom URL and API key, we're happy to add a one-paragraph description with a link and instructions on the URL to use
* For any other model that requires more logic, we recommend you release your own Python package `pydantic-ai-xxx`, which depends on [`pydantic-ai-slim`](install.md#slim-install) and implements a model that inherits from our [`Model`][pydantic_ai.models.Model] ABC

If you're unsure about adding a model, please [create an issue](https://github.com/pydantic/pydantic-ai/issues).
