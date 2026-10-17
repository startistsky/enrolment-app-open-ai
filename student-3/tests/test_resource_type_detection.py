"""Regression tests for campus resource type detection."""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import detect_resource_types  # noqa: E402


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Find an available study room for 6 students",
            {"Study Room"},
        ),
        (
            "Find a computer lab",
            {"Computer Lab"},
        ),
        (
            "Find a study room or computer lab",
            {"Study Room", "Computer Lab"},
        ),
        (
            "Find an available computer lab",
            {"Computer Lab"},
        ),
    ],
)
def test_resource_type_detection(question, expected):
    """Match intended types without substring false positives."""
    assert detect_resource_types(question) == expected
