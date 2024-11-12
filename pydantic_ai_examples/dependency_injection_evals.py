from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Literal, get_args

from pydantic_ai import Agent, Depends, dependency_provider
from pydantic_ai.models.gemini import GeminiModel

# Define possible tags
ReviewTag = Literal[
    'good food quality',
    'average food quality',
    'bad food quality',
    'good customer service',
    'bad customer service',
    'long waits',
    'order mix-ups',
    'good atmosphere',
    'other complaint',
    'other compliment',
]


# Define the response type
@dataclass
class ReviewAnalysisResponse:
    score: int  # Between -5 (most negative) and +5 (most positive)
    tags: list[ReviewTag]  # Extracted tags from the review


Response = ReviewAnalysisResponse

# Create the agent
agent = Agent[None, Response](
    result_type=Response,
    retries=2,
    model=GeminiModel('gemini-1.5-flash', api_key='<OMITTED>'),
)


# Define training examples
@dataclass
class TrainingExample:
    text: str
    score: int
    tags: list[ReviewTag]


@cache
def get_examples() -> list[TrainingExample]:
    """Get training examples to use when building the system prompt.

    Note 1: we could use an external file or database to store examples in a real-world scenario.
    In this case, it may be useful to use CallContext and/or dependency injection to obtain resources used to obtain
    the examples, especially if the examples or other input we want to provide to the prompt might be user-managed or
    otherwise updating in real time.

    Note 2: Returning examples in a function allows us to use dependency injection to easily override the set of
    examples used while building the prompt. This allows us to evaluate our agent's performance using cross-validation.
    """
    return [
        TrainingExample(
            text='The food was amazing and the service was excellent.',
            score=5,
            tags=['good food quality', 'good customer service'],
        ),
        TrainingExample(
            text='I waited an hour for my food, and it was cold when it arrived.',
            score=-4,
            tags=['long waits', 'bad food quality'],
        ),
        TrainingExample(
            text='The waiter mixed up our orders and was very rude.',
            score=-3,
            tags=['order mix-ups', 'bad customer service'],
        ),
        TrainingExample(
            text='Great atmosphere, but the food was just okay.',
            score=1,
            tags=['good atmosphere', 'average food quality'],
        ),
        TrainingExample(
            text='The food was terrible, but the staff were friendly.',
            score=-2,
            tags=['bad food quality', 'good customer service'],
        ),
        TrainingExample(
            text='Amazing dishes and wonderful service!',
            score=5,
            tags=['good food quality', 'good customer service'],
        ),
    ]


@dataclass
class SystemPromptBuilder:
    """This class builds the system prompt for the agent.

    We use a class to build the system prompt so that we can easily override different aspects of the prompt building,
    making it easier to compare different approaches. While this might feel like overkill in this example, this can
    be useful in more complex scenarios where the prompt-building might make use of lots of different context about the
    user or other resources.

    We'll see below how we can leverage dependency injection to easily change the behavior of the system prompt builder.
    """

    examples: list[TrainingExample]

    def build_prompt(self) -> str:
        return f'{self._get_task_description()}\n\n{self._get_examples_text()}\n\n{self._final_notes()}'

    @staticmethod
    def _get_task_description():
        tags_list = get_args(ReviewTag)
        return (
            'You are a restaurant review analysis assistant.\n'
            'For each review, provide a score between -5 (most negative) and +5 (most positive), '
            'and extract relevant tags from the following list:\n'
            f'{tags_list}.'
        )

    def _get_examples_text(self):
        return 'Here are some examples:\n' + '\n\n'.join(
            [f"Review: '{ex.text}'\nScore: {ex.score}\nLabels: {', '.join(ex.tags)}" for ex in self.examples]
        )

    def _final_notes(self) -> str:
        return 'Now, analyze the following review.'


def build_prompt(examples: list[TrainingExample] = Depends(get_examples)) -> str:
    """Build the system prompt from the examples.

    Obtaining the examples through dependency injection will make it easier to override the examples used
    during evaluation.
    """
    return SystemPromptBuilder(examples).build_prompt()


# Set the system prompt for the agent
@agent.system_prompt
def get_system_prompt(prompt: str = Depends(build_prompt)) -> str:
    """Get the system prompt.

    While this function may seem simple enough to be unnecessary, obtaining the prompt through dependency injection
    will make it easier to override the logic used to produce the prompt. In particular, it ends up being
    straightforward to replace `build_prompt` with a function that uses a different prompt builder.

    That said, it might be nice if we could override this get_system_prompt function more directly.
    (It should be straightforward to automatically wrap the @agent.system_prompt decorator in a way
    that you can override the function it decorates directly, if we want to go down that route.)
    """
    return prompt


async def handle_user_request(text: str) -> Response:
    """Handle a user request by running the agent on the provided text.

    While this function is simple in this example, it could be more complex in a real-world scenario.
    For example, it might make requests to various services to obtain additional context for the agent.

    In our evaluation code below, we make direct use of this function, and this is important, because in
    real-world examples it may not always be as practical to make calls with the agent in isolation.
    (E.g., if the agent requires a great deal of data for a single run, and that data is easily queried from a database,
    but painful to move into a fully-isolated evaluation harness.)
    """
    result = await agent.run(text)
    return result.data


@dataclass
class EvaluationResult:
    """A simple container for the results of evaluating the agent on a single example."""

    text: str
    expected_score: int
    actual_score: int
    expected_tags: list[ReviewTag]
    actual_tags: list[ReviewTag]


async def get_agent_evaluation_results() -> list[EvaluationResult]:
    """Get the evaluation results for the agent.

    This function evaluates the agent on each example in the training set, comparing the agent's output to the
    expected output. It returns a list of EvaluationResult objects, which can be used to compute metrics.
    """
    all_examples = get_examples()
    results: list[EvaluationResult] = []
    for i, validation_example in enumerate(all_examples):
        # Remove the validation example from the training examples:
        training_examples = all_examples.copy()
        training_examples.pop(i)

        # Run the agent on the validation example, using only the training examples to build the prompt:
        with dependency_provider.scope(get_examples, lambda: training_examples):
            actual_response = await handle_user_request(validation_example.text)

        # Store the results for evaluation:
        results.append(
            EvaluationResult(
                text=validation_example.text,
                expected_score=validation_example.score,
                actual_score=actual_response.score,
                expected_tags=validation_example.tags,
                actual_tags=actual_response.tags,
            )
        )
    return results


# Now we translate the evaluation results into quantitative metrics
def f1_score(expected: Sequence[str], actual: Sequence[str]) -> float:
    """Compute the F1 score for the tags extracted by the agent."""
    expected_set = set(expected)
    actual_set = set(actual)
    true_positives = len(expected_set & actual_set)
    if not expected_set and not actual_set:
        return 1.0  # Perfect match if both are empty
    if not actual_set:
        return 0.0
    precision = true_positives / len(actual_set)
    recall = true_positives / len(expected_set)
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def compute_metrics(results: list[EvaluationResult]):
    """Compute the average score error and average F1 score for the tags extracted by the agent."""
    total_score_error = 0.0
    total_f1 = 0.0
    for result in results:
        score_error = abs(result.expected_score - result.actual_score)
        total_score_error += score_error
        f1 = f1_score(result.expected_tags, result.actual_tags)
        total_f1 += f1
    average_score_error = total_score_error / len(results)
    average_f1 = total_f1 / len(results)
    return average_score_error, average_f1


async def evaluate_agent():
    """Evaluate the agent and print the results."""
    results = await get_agent_evaluation_results()
    score_error, f1 = compute_metrics(results)
    print('Average Score Error:', score_error)
    print('Average F1 Score for Labels:', f1)


# Okay, now let's leverage the modular design of our SystemPromptBuilder and our dependency injection system to
# evaluate the impact on our agent of making changes deeper in the system prompt building process:


class AlternateSystemPromptBuilder(SystemPromptBuilder):
    """Add some additional notes to the system prompt to emphasize the importance of food quality in the reviews."""

    def _final_notes(self) -> str:
        return (
            'Note: We are primarily concerned with the quality of the food. '
            'Place the highest emphasis on comments about food quality when determining the score, '
            'with comparatively lower emphasis on complaints about service, wait times, etc.\n\n'
            + super()._final_notes()
        )


async def compare_system_prompt_builders():
    """Evaluate the agent using two different system prompt builders.

    We first use the base SystemPromptBuilder, then override the build_prompt dependency to use the
    AlternateSystemPromptBuilder and evaluate the agent again to see the impact on the agent's performance.
    """
    # Evaluate with the base prompt builder
    print('Evaluating base SystemPromptBuilder:')
    await evaluate_agent()

    # Override the build_prompt dependency to use the alternate prompt builder
    def build_alternate_prompt(examples: list[TrainingExample] = Depends(get_examples)) -> str:
        return AlternateSystemPromptBuilder(examples).build_prompt()

    with dependency_provider.scope(build_prompt, build_alternate_prompt):
        print('\nEvaluating AlternateSystemPromptBuilder:')
        await evaluate_agent()  # This will print the results using the AlternateSystemPromptBuilder


if __name__ == '__main__':
    import anyio

    anyio.run(compare_system_prompt_builders)
    """
    Evaluating base SystemPromptBuilder:
    Average Score Error: 0.3333333333333333
    Average F1 Score for Labels: 1.0

    Evaluating AlternateSystemPromptBuilder:
    Average Score Error: 0.5
    Average F1 Score for Labels: 1.0
    """
