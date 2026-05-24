"""Checkout shim for running the src-layout package with ``python -m``.

When this repository is the current working directory, Python sees this root
package before it sees ``src/readme_first_screen``.  Point the package at the
local src implementation so direct module execution cannot fall through to an
older installed copy.
"""

from pathlib import Path

_src_package = Path(__file__).resolve().parents[1] / "src" / __name__
_src_init = _src_package / "__init__.py"

if not _src_init.is_file():
    raise ImportError(f"Cannot find local source package at {_src_init}")

__file__ = str(_src_init)
__path__ = [str(_src_package)]

with _src_init.open("rb") as _source:
    exec(compile(_source.read(), str(_src_init), "exec"), globals(), globals())

del Path, _source, _src_init, _src_package
