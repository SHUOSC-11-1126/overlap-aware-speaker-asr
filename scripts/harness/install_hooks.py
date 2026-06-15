"""Install this repository's git hooks via core.hooksPath.

Python port of code-tape's scripts/workflows/install-hooks.mjs. Pointing
``core.hooksPath`` at the tracked ``.githooks`` directory means the hooks are
versioned with the repo and shared by every clone -- no per-developer copying
into ``.git/hooks``. Skipped in CI, where hooks must not run.
"""

from __future__ import annotations

import os
import subprocess
import sys


def install_hooks():
    if os.environ.get("CI"):
        print("Skipping git hook installation in CI.")
        return 0
    try:
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as err:
        print(f"failed to install git hooks: {err}", file=sys.stderr)
        return 1
    print("Git hooks installed via core.hooksPath=.githooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(install_hooks())
