"""Sanity import test for every ti_* package.

Fails if any workspace package cannot be imported. Cheap coverage for
package boundary issues (missing __init__, circular imports, syntax errors).
"""

from __future__ import annotations

import importlib

import pytest

PACKAGES = [
    "ti_core",
    "ti_data",
    "ti_strategy",
    "ti_analysis",
    "ti_backtest",
    "ti_risk",
    "ti_execution",
    "ti_ml",
    "ti_agents",
    "ti_ui",
]


@pytest.mark.parametrize("pkg_name", PACKAGES)
def test_package_imports(pkg_name: str) -> None:
    """Every workspace package must import cleanly."""
    module = importlib.import_module(pkg_name)
    assert hasattr(module, "__version__"), f"{pkg_name} missing __version__"
    assert isinstance(module.__version__, str)
