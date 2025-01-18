# Installation

PydanticAI is available on PyPI as [`pydantic-ai`](https://pypi.org/project/pydantic-ai/) so installation is as simple as:

```bash
pip/uv-add pydantic-ai
```

(Requires Python 3.9+)

This installs the `pydantic_ai` package, core dependencies, and libraries required to use all the models
included in PydanticAI. If you want to use a specific model, you can install the ["slim"](#slim-install) version of PydanticAI.

## Use with Pydantic Logfire

PydanticAI has an excellent (but completely optional) integration with [Pydantic Logfire](https://pydantic.dev/logfire) to help you view and understand agent runs.

To use Logfire with PydanticAI, install `pydantic-ai` or `pydantic-ai-slim` with the `logfire` optional group:

```bash
pip/uv-add 'pydantic-ai[logfire]'
```

From there, follow the [Logfire setup docs](logfire.md#using-logfire) to configure Logfire.

## Running Examples

We distribute the [`pydantic_ai_examples`](https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_examples) directory as a separate PyPI package ([`pydantic-ai-examples`](https://pypi.org/project/pydantic-ai-examples/)) to make examples extremely easy to customize and run.

To install examples, use the `examples` optional group:

```bash
pip/uv-add 'pydantic-ai[examples]'
```

To run the examples, follow instructions in the [examples docs](examples/index.md).

## Slim Install

If you know which model you're going to use and want to avoid installing superfluous packages, you can use the [`pydantic-ai-slim`](https://pypi.org/project/pydantic-ai-slim/) package.
For example, if you're using just [`OpenAIModel`][pydantic_ai.models.openai.OpenAIModel], you would run:

```bash
pip/uv-add 'pydantic-ai-slim[openai]'
```

`pydantic-ai-slim` has the following optional groups:

* `logfire` — installs [`logfire`](logfire.md) [PyPI ↗](https://pypi.org/project/logfire){:target="_blank"}
* `graph` - installs [`pydantic-graph`](graph.md) [PyPI ↗](https://pypi.org/project/pydantic-graph){:target="_blank"}
* `openai` — installs `openai` [PyPI ↗](https://pypi.org/project/openai){:target="_blank"}
* `vertexai` — installs `google-auth` [PyPI ↗](https://pypi.org/project/google-auth){:target="_blank"} and `requests` [PyPI ↗](https://pypi.org/project/requests){:target="_blank"}
* `anthropic` — installs `anthropic` [PyPI ↗](https://pypi.org/project/anthropic){:target="_blank"}
* `groq` — installs `groq` [PyPI ↗](https://pypi.org/project/groq){:target="_blank"}
* `mistral` — installs `mistralai` [PyPI ↗](https://pypi.org/project/mistralai){:target="_blank"}

See the [models](models.md) documentation for information on which optional dependencies are required for each model.

You can also install dependencies for multiple models and use cases, for example:

```bash
pip/uv-add 'pydantic-ai-slim[openai,vertexai,logfire]'
```
