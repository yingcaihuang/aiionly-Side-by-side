"""
Test basic project structure and imports.
"""

import pytest
from pathlib import Path


def test_project_structure():
    """Test that the basic project structure exists."""
    # Check main package
    assert Path("model_comparison_system").exists()
    assert Path("model_comparison_system/__init__.py").exists()
    
    # Check subpackages
    assert Path("model_comparison_system/config").exists()
    assert Path("model_comparison_system/api").exists()
    assert Path("model_comparison_system/services").exists()
    assert Path("model_comparison_system/ui").exists()
    
    # Check configuration files
    assert Path("config.yaml.example").exists()
    assert Path("requirements.txt").exists()
    assert Path("pyproject.toml").exists()
    assert Path("README.md").exists()


def test_package_imports():
    """Test that basic package imports work."""
    import model_comparison_system
    assert hasattr(model_comparison_system, '__version__')
    
    # Test subpackage imports
    from model_comparison_system import config
    from model_comparison_system import api
    from model_comparison_system import services
    from model_comparison_system import ui


def test_logging_config_import():
    """Test that logging configuration can be imported."""
    from model_comparison_system.config.logging_config import setup_logging, get_logger
    
    # Test basic functionality
    logger = get_logger('test')
    assert logger.name == 'model_comparison_system.test'