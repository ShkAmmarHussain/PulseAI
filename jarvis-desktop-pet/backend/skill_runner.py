"""Tiny sandbox runner for Mini World skills in packaged builds (doc 37 sprint 8).

Built as its own small exe (skill-runner.spec -> pulseai-skill-runner.exe) so a
skill starts in about a second, instead of unpacking the whole backend exe.
It runs skill.py from the current (throwaway) folder, exactly like
``python -I runner.py`` does in development.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.world.skills_lab import run_skill_main  # noqa: E402

if __name__ == "__main__":
    sys.exit(run_skill_main())
