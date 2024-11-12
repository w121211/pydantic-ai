from importlib.metadata import version

from ._depends import Depends, DependsType, inject
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
    'inject',
)
__version__ = version('pydantic_ai')
