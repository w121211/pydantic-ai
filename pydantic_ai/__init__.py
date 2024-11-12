from importlib.metadata import version

from ._depends import Depends, DependsType, Provider, dependency_provider
from .agent import Agent
from .dependencies import CallContext
from .exceptions import ModelRetry, UnexpectedModelBehaviour, UserError

__all__ = (
    'Agent',
    'CallContext',
    'ModelRetry',
    'UnexpectedModelBehaviour',
    'UserError',
    '__version__',
    'Depends',
    'DependsType',
    'Provider',
    'dependency_provider',
)
__version__ = version('pydantic_ai')
