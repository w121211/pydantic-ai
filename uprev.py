"""Update the pydantic-ai version number everywhere.

Because we have multiple packages which depend on one-another,
we have to update the version number in:
* pyproject.toml
* pydantic_ai_examples/pyproject.toml
* pydantic_ai_slim/pyproject.toml

Usage:

    uv run uprev.py <new_version_number>
"""

import re
import subprocess
import sys

from pathlib import Path

ROOT_DIR = Path(__file__).parent

try:
    version = sys.argv[1]
except IndexError:
    print('Usage: uv run uprev.py <new_version_number>', file=sys.stderr)
    sys.exit(1)


old_version: str | None = None


def sub_version(m: re.Match[str]) -> str:
    global old_version
    prefix = m.group(1)
    quote = m.group(2)
    old_version = m.group(3)
    return f'{prefix}{quote}{version}{quote}'


root_pp = ROOT_DIR / 'pyproject.toml'
root_pp_text = root_pp.read_text()
root_pp_text, _ = re.subn(r'^(version ?= ?)(["\'])(.+)\2$', sub_version, root_pp_text, 1, flags=re.M)

if old_version is None:
    print('ERROR: Could not find version in root pyproject.toml', file=sys.stderr)
    sys.exit(1)

print(f'Updating version from {old_version!r} to {version!r}')


def replace_deps_version(text: str) -> tuple[str, int]:
    ovr = re.escape(old_version)
    text, c = re.subn(f'(pydantic-ai-.+?==){ovr}', fr'\g<1>{version}', text, count=5)
    text, c2 = re.subn(
        fr'^(version ?= ?)(["\']){ovr}\2$', fr'\g<1>\g<2>{version}\g<2>', text, count=5, flags=re.M
    )
    return text, c + c2


root_pp_text, count_root = replace_deps_version(root_pp_text)

examples_pp = ROOT_DIR / 'examples' / 'pyproject.toml'
examples_pp_text = examples_pp.read_text()
examples_pp_text, count_ex = replace_deps_version(examples_pp_text)

slim_pp = ROOT_DIR / 'pydantic_ai_slim' / 'pyproject.toml'
slim_pp_text = slim_pp.read_text()
slim_pp_text, count_slim = replace_deps_version(slim_pp_text)

if count_root == 2 and count_ex == 2 and count_slim == 1:
    root_pp.write_text(root_pp_text)
    examples_pp.write_text(examples_pp_text)
    slim_pp.write_text(slim_pp_text)
    print('running `make sync`...')
    subprocess.run(['make', 'sync'], check=True)
    print(f'running `git switch -c uprev-{version}`...')
    subprocess.run(['git', 'switch', '-c', f'uprev-{version}'], check=True)
    print(
        f'SUCCESS: replaced version in\n'
        f'  {root_pp}\n'
        f'  {examples_pp}\n'
        f'  {slim_pp}'
    )
else:
    print(
        f'ERROR:\n'
        f'  {count_root} version references in {root_pp} (expected 2)\n'
        f'  {count_ex} version references in {examples_pp} (expected 2)\n'
        f'  {count_slim} version references in {slim_pp} (expected 1)',
        file=sys.stderr,
    )
    sys.exit(1)
