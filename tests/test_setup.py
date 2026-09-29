"""Smoke test: pytest should pass once all libraries are installed."""
import importlib
import sys

import pytest

REQUIRED = ["pandas", "numpy", "streamlit", "plotly", "scipy", "openpyxl"]


def test_python_version():
    assert sys.version_info >= (3, 11)


@pytest.mark.parametrize("name", REQUIRED)
def test_library_imports(name):
    importlib.import_module(name)
