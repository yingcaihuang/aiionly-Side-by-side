"""
Pytest configuration and fixtures for the Model Comparison System tests.
"""

import pytest
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "api": {
            "base_url": "https://maas.aiionly.com",
            "api_key": "test-api-key",
            "timeout": 30,
            "max_retries": 3
        },
        "models": {
            "supported_models": [
                "glm-4.6v-flash",
                "gpt-oss-120b", 
                "grok-4",
                "gemini-2.5-flash"
            ],
            "default_models": [
                "glm-4.6v-flash",
                "gpt-oss-120b",
                "grok-4",
                "gemini-2.5-flash"
            ],
            "max_parallel_calls": 4
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "test_model_comparison.log"
        }
    }


@pytest.fixture
def temp_config_file(tmp_path: Path, sample_config: Dict[str, Any]) -> Path:
    """Create a temporary configuration file for testing."""
    import yaml
    
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f)
    
    return config_file