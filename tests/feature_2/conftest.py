"""
Pytest configuration for feature_2 tests.
Provides fixtures for module argument testing.
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock

# Add project source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py/src"))


def create_mock_args(**kwargs):
    """Create a mock args object with specified attributes"""
    args = Mock()
    for key, value in kwargs.items():
        setattr(args, key, value)
    return args


def create_mock_module(
    main_return=True, buildargs_return=None, has_main=True, has_doc=True
):
    """
    Create a mock module with configurable properties.

    Args:
        main_return: Value to return from main()
        buildargs_return: Value to return from buildargs()
        has_main: Whether module has main() function
        has_doc: Whether module has __doc__ string

    Returns:
        Mock module object
    """
    module = Mock()

    if has_main:
        module.main = Mock(return_value=main_return)

    if has_doc:
        module.__doc__ = "Mock module for testing"

    # buildargs can return None or a parser
    if buildargs_return is not None:
        module.buildargs = Mock(return_value=buildargs_return)
    else:
        # Default: return None (no custom args)
        module.buildargs = Mock(return_value=None)

    module.init = Mock(return_value=True)
    module.access = Mock(return_value=True)

    return module
