"""Draws heavily from the fast_depends library, but with some important differences in behavior.

In particular:
* No pydantic validation is performed on inputs to/outputs from function calls
* No support for extra_dependencies
* No support for custom field types
* You can call injected functions and pass values for arguments that would have been injected.
    When this happens, the dependency function is not called and the passed value is used instead.
    In fast_depends, the dependency function is always called and provided arguments are ignored.
"""

from .depends import Depends, inject
from .models import Depends as DependsType
from .provider import Provider, dependency_provider

__all__ = ('Depends', 'inject', 'DependsType', 'Provider', 'dependency_provider')
