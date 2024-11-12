import sys
from importlib.metadata import version as get_version

__all__ = ('ExceptionGroup',)
ANYIO_V3 = get_version('anyio').startswith('3.')

if ANYIO_V3:
    from anyio import ExceptionGroup as ExceptionGroup  # type: ignore
else:
    if sys.version_info < (3, 11):
        from exceptiongroup import ExceptionGroup as ExceptionGroup
    else:
        ExceptionGroup = ExceptionGroup
