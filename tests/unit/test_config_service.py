"""Unit tests for configuration service."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from model_comparison_system.config.config_service import ConfigService, ConfigurationError
from model_comparison_system.config.models import Config, ApiSettings, ModelSettings, LoggingSettings


class TestConfigService:
    """Test cases for ConfigService."""
    
    def test_load_valid_config(self, temp_config_file):
        """Test loading a valid configuration file."""
        config_service = ConfigService(str(temp_config_file))
        config = config_service.load_config()
        
        assert isinstance(config, Config)
        assert config.api.base_url == "https://maas.aiionly.com"
        assert config.api.api_key == "test-api-key"
        assert config.api.timeout == 30
        assert config.api.max_retries == 3
        
        assert len(config.models.supported_models) == 4
        assert "glm-4.6v-flash" in config.models.supported_models
        assert config.models.max_parallel_calls == 4
        
        assert config.logging.level == "INFO"
    
    def test_load_config_file_not_found(self):
        """Test loading configuration when file doesn't exist."""
        config_service = ConfigService("nonexistent.yaml")
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.load_config()
        
        assert "Configuration file not found" in str(exc_info.value)
    
    def test_load_empty_config_file(self, tmp_path):
        """Test loading an empty configuration file."""
        empty_config = tmp_path / "empty.yaml"
        empty_config.write_text("")
        
        config_service = ConfigService(str(empty_config))
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.load_config()
        
        assert "Configuration file is empty" in str(exc_info.value)
    
    def test_load_invalid_yaml(self, tmp_path):
        """Test loading a file with invalid YAML syntax."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [")
        
        config_service = ConfigService(str(invalid_yaml))
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.load_config()
        
        assert "Invalid YAML format" in str(exc_info.value)
    
    def test_load_config_with_validation_errors(self, tmp_path):
        """Test loading configuration with validation errors."""
        invalid_config = {
            "api": {
                "base_url": "invalid-url",  # Invalid URL format
                "api_key": "",  # Empty API key
                "timeout": -1,  # Invalid timeout
            },
            "models": {
                "supported_models": [],  # Empty list
                "default_models": ["invalid-model"],
                "max_parallel_calls": 0  # Invalid value
            }
        }
        
        config_file = tmp_path / "invalid_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        config_service = ConfigService(str(config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.load_config()
        
        assert "Configuration validation failed" in str(exc_info.value)
    
    def test_get_api_settings_without_loading(self):
        """Test getting API settings without loading configuration first."""
        config_service = ConfigService("config.yaml")
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.get_api_settings()
        
        assert "Configuration not loaded" in str(exc_info.value)
    
    def test_get_model_settings_without_loading(self):
        """Test getting model settings without loading configuration first."""
        config_service = ConfigService("config.yaml")
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.get_model_settings()
        
        assert "Configuration not loaded" in str(exc_info.value)
    
    def test_get_logging_settings_without_loading(self):
        """Test getting logging settings without loading configuration first."""
        config_service = ConfigService("config.yaml")
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.get_logging_settings()
        
        assert "Configuration not loaded" in str(exc_info.value)
    
    def test_get_config_without_loading(self):
        """Test getting complete config without loading configuration first."""
        config_service = ConfigService("config.yaml")
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.get_config()
        
        assert "Configuration not loaded" in str(exc_info.value)
    
    def test_get_settings_after_loading(self, temp_config_file):
        """Test getting settings after loading configuration."""
        config_service = ConfigService(str(temp_config_file))
        config_service.load_config()
        
        api_settings = config_service.get_api_settings()
        assert isinstance(api_settings, ApiSettings)
        assert api_settings.api_key == "test-api-key"
        
        model_settings = config_service.get_model_settings()
        assert isinstance(model_settings, ModelSettings)
        assert len(model_settings.supported_models) == 4
        
        logging_settings = config_service.get_logging_settings()
        assert isinstance(logging_settings, LoggingSettings)
        assert logging_settings.level == "INFO"
        
        complete_config = config_service.get_config()
        assert isinstance(complete_config, Config)
    
    def test_reload_config(self, temp_config_file):
        """Test reloading configuration."""
        config_service = ConfigService(str(temp_config_file))
        
        # Load initial config
        config1 = config_service.load_config()
        assert config1.api.api_key == "test-api-key"
        
        # Modify the config file
        modified_config = {
            "api": {
                "base_url": "https://maas.aiionly.com",
                "api_key": "new-test-key",
                "timeout": 60,
                "max_retries": 5
            },
            "models": {
                "supported_models": ["glm-4.6v-flash"],
                "default_models": ["glm-4.6v-flash"],
                "max_parallel_calls": 1
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(message)s",
                "file": "test.log"
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(modified_config, f)
        
        # Reload config
        config2 = config_service.reload_config()
        assert config2.api.api_key == "new-test-key"
        assert config2.api.timeout == 60
        assert config2.logging.level == "DEBUG"
    
    def test_validate_config_valid(self, sample_config):
        """Test validating a valid configuration."""
        config = Config(**sample_config)
        config_service = ConfigService()
        
        errors = config_service.validate_config(config)
        assert errors == []
    
    def test_validate_config_with_errors(self):
        """Test validating configuration with errors."""
        # Create config with cross-field constraint violation
        invalid_config_data = {
            "api": {
                "base_url": "https://maas.aiionly.com",
                "api_key": "test-key",
                "timeout": 30,
                "max_retries": 3
            },
            "models": {
                "supported_models": ["model1", "model2"],
                "default_models": ["model1"],
                "max_parallel_calls": 5  # More than default models
            },
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file": "test.log"
            }
        }
        
        config = Config(**invalid_config_data)
        config_service = ConfigService()
        
        errors = config_service.validate_config(config)
        assert len(errors) > 0
        assert any("max_parallel_calls" in error for error in errors)
    
    def test_validate_startup_configuration_placeholder_api_key(self, tmp_path):
        """Test startup validation with placeholder API key."""
        config_data = {
            "api": {
                "base_url": "https://maas.aiionly.com",
                "api_key": "your-api-key-here",  # Placeholder value
                "timeout": 30,
                "max_retries": 3
            },
            "models": {
                "supported_models": ["glm-4.6v-flash"],
                "default_models": ["glm-4.6v-flash"],
                "max_parallel_calls": 1
            },
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file": "test.log"
            }
        }
        
        config_file = tmp_path / "placeholder_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config_service = ConfigService(str(config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.validate_startup_configuration()
        
        assert "placeholder value" in str(exc_info.value)
    
    def test_validate_startup_configuration_no_default_models(self, tmp_path):
        """Test startup validation with no default models."""
        config_data = {
            "api": {
                "base_url": "https://maas.aiionly.com",
                "api_key": "valid-key",
                "timeout": 30,
                "max_retries": 3
            },
            "models": {
                "supported_models": ["glm-4.6v-flash"],
                "default_models": [],  # Empty default models
                "max_parallel_calls": 1
            },
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file": "test.log"
            }
        }
        
        config_file = tmp_path / "no_defaults_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config_service = ConfigService(str(config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            config_service.validate_startup_configuration()
        
        assert "default_models cannot be empty" in str(exc_info.value)
    
    def test_create_default_config_file(self, tmp_path):
        """Test creating a default configuration file."""
        config_path = tmp_path / "default_config.yaml"
        
        ConfigService.create_default_config_file(str(config_path))
        
        assert config_path.exists()
        
        # Load and validate the created config
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        assert 'api' in config_data
        assert 'models' in config_data
        assert 'logging' in config_data
        assert config_data['api']['api_key'] == 'your-api-key-here'
        assert len(config_data['models']['supported_models']) == 4
    
    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_create_default_config_file_permission_error(self, mock_file):
        """Test creating default config file with permission error."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigService.create_default_config_file("readonly_config.yaml")
        
        assert "Cannot create default configuration file" in str(exc_info.value)