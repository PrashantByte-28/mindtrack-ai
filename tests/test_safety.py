
import sys
from pathlib import Path

import pytest

# Add the project root and src to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
for _p in (str(SRC_DIR), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from mindtrack_ai.safety import check_message_safety


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("I want to kill myself.", True),
        ("I don't want to die.", False),
        (
            "I feel hopeless and don't know how to cope anymore.",
            False,
        ),
        (
            "I don't want to die, but I might hurt myself.",
            True,
        ),
        ("I am stressed about my assignments.", False),
        ("I feel happy today.", False),
        ("", False),
    ],
)
def test_check_message_safety(message, expected):
    assert check_message_safety(message) is expected