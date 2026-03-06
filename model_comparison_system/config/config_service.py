"""Configuration service for loading and validating application configuration."""

import os
import yaml
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import ValidationError

from .models import Config, ApiSettings, ModelSettings, LoggingSettings


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class ConfigService:
    """Service for loading, validating, and managing application configuration."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize ConfigService with configuration file path.
        
        Args:
            config_path: Path to the configuration file (default: config.yaml)
        """
        self.config_path = Path(config_path)
        self._config: Optional[Config] = None
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> Config:
        """Load and validate configuration from file.
        
        Returns:
            Config: Validated configuration object
            
        Raises:
            ConfigurationError: If configuration file is missing, invalid, or fails validation
        """
        try:
            # Check if config file exists
            if not self.config_path.exists():
                raise ConfigurationError(
                    f"Configuration file not found: {self.config_path.absolute()}"
                )
            
            # Load YAML content
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
            
            if config_data is None:
                raise ConfigurationError("Configuration file is empty")
            
            # Validate configuration using Pydantic models
            try:
                config = Config(**config_data)
            except ValidationError as e:
                error_details = self._format_validation_errors(e)
                raise ConfigurationError(
                    f"Configuration validation failed:\n{error_details}"
                )
            
            # Perform cross-field validation
            cross_field_errors = config.validate_cross_field_constraints()
            if cross_field_errors:
                raise ConfigurationError(
                    f"Configuration validation failed:\n" + 
                    "\n".join(f"- {error}" for error in cross_field_errors)
                )
            
            self._config = config
            self.logger.info(f"Configuration loaded successfully from {self.config_path}")
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML format in configuration file: {e}")
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Unexpected error loading configuration: {e}")
    
    def validate_config(self, config: Config) -> List[str]:
        """Validate a configuration object and return any validation errors.
        
        Args:
            config: Configuration object to validate
            
        Returns:
            List[str]: List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            # Validate using Pydantic
            config.dict()  # This triggers validation
            
            # Check cross-field constraints
            cross_field_errors = config.validate_cross_field_constraints()
            errors.extend(cross_field_errors)
            
        except ValidationError as e:
            errors.extend(self._extract_validation_errors(e))
        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")
        
        return errors
    
    def get_api_settings(self) -> ApiSettings:
        """Get API configuration settings.
        
        Returns:
            ApiSettings: API configuration
            
        Raises:
            ConfigurationError: If configuration is not loaded
        """
        if self._config is None:
            raise ConfigurationError("Configuration not loaded. Call load_config() first.")
        return self._config.api
    
    def get_model_settings(self) -> ModelSettings:
        """Get model configuration settings.
        
        Returns:
            ModelSettings: Model configuration
            
        Raises:
            ConfigurationError: If configuration is not loaded
        """
        if self._config is None:
            raise ConfigurationError("Configuration not loaded. Call load_config() first.")
        return self._config.models
    
    def get_logging_settings(self) -> LoggingSettings:
        """Get logging configuration settings.
        
        Returns:
            LoggingSettings: Logging configuration
            
        Raises:
            ConfigurationError: If configuration is not loaded
        """
        if self._config is None:
            raise ConfigurationError("Configuration not loaded. Call load_config() first.")
        return self._config.logging
    
    def get_config(self) -> Config:
        """Get the complete configuration object.
        
        Returns:
            Config: Complete configuration
            
        Raises:
            ConfigurationError: If configuration is not loaded
        """
        if self._config is None:
            raise ConfigurationError("Configuration not loaded. Call load_config() first.")
        return self._config
    
    def reload_config(self) -> Config:
        """Reload configuration from file.
        
        Returns:
            Config: Reloaded configuration object
            
        Raises:
            ConfigurationError: If configuration file is invalid or fails validation
        """
        self._config = None
        return self.load_config()
    
    def validate_startup_configuration(self) -> None:
        """Validate configuration during application startup.
        
        This method performs comprehensive validation and raises detailed errors
        for startup configuration issues.
        
        Raises:
            ConfigurationError: If any configuration validation fails
        """
        try:
            config = self.load_config()
            
            # Additional startup-specific validations
            startup_errors = []
            
            # Validate API key is not placeholder
            if config.api.api_key == "your-api-key-here":
                startup_errors.append(
                    "API key is set to placeholder value. Please update config.yaml with a valid API key."
                )
            
            # Validate log file directory exists (if file logging is configured)
            if config.logging.file:
                log_path = Path(config.logging.file)
                log_dir = log_path.parent
                if not log_dir.exists():
                    try:
                        log_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        startup_errors.append(f"Cannot create log directory {log_dir}: {e}")
            
            # Validate model configuration
            if not config.models.default_models:
                startup_errors.append("No default models configured")
            
            if startup_errors:
                raise ConfigurationError(
                    "Startup configuration validation failed:\n" +
                    "\n".join(f"- {error}" for error in startup_errors)
                )
                
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Startup configuration validation failed: {e}")
    
    def _format_validation_errors(self, validation_error: ValidationError) -> str:
        """Format Pydantic validation errors into readable format.
        
        Args:
            validation_error: Pydantic ValidationError
            
        Returns:
            str: Formatted error message
        """
        errors = []
        for error in validation_error.errors():
            field_path = " -> ".join(str(loc) for loc in error['loc'])
            message = error['msg']
            errors.append(f"- {field_path}: {message}")
        
        return "\n".join(errors)
    
    def _extract_validation_errors(self, validation_error: ValidationError) -> List[str]:
        """Extract validation errors as a list of strings.
        
        Args:
            validation_error: Pydantic ValidationError
            
        Returns:
            List[str]: List of error messages
        """
        errors = []
        for error in validation_error.errors():
            field_path = " -> ".join(str(loc) for loc in error['loc'])
            message = error['msg']
            errors.append(f"{field_path}: {message}")
        
        return errors
    
    @staticmethod
    def create_default_config_file(config_path: str = "config.yaml") -> None:
        """Create a default configuration file.
        
        Args:
            config_path: Path where to create the configuration file
            
        Raises:
            ConfigurationError: If file cannot be created
        """
        default_config = {
            'api': {
                'base_url': 'https://maas.aiionly.com',
                'api_key': 'your-api-key-here',
                'timeout': 30,
                'max_retries': 3
            },
            'models': {
                'supported_models': [
                    'glm-4.6v-flash',
                    'gpt-oss-120b',
                    'grok-4',
                    'gemini-2.5-flash'
                ],
                'default_models': [
                    'glm-4.6v-flash',
                    'gpt-oss-120b',
                    'grok-4',
                    'gemini-2.5-flash'
                ],
                'max_parallel_calls': 4
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'model_comparison.log'
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as file:
                yaml.dump(default_config, file, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigurationError(f"Cannot create default configuration file: {e}")