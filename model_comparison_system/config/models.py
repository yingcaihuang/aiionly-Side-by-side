"""Configuration data models with Pydantic validation."""

from typing import List, Optional
from pydantic import BaseModel, Field, validator
import logging


class ApiSettings(BaseModel):
    """API configuration settings for MAAS API."""
    
    base_url: str = Field(
        default="https://maas.aiionly.com",
        description="Base URL for the MAAS API"
    )
    api_key: str = Field(
        ...,
        description="API key for authentication with MAAS API"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts"
    )
    
    @validator('base_url')
    def validate_base_url(cls, v):
        """Validate that base_url is a proper URL."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        if v.endswith('/'):
            v = v.rstrip('/')
        return v
    
    @validator('api_key')
    def validate_api_key(cls, v):
        """Validate that API key is not empty or placeholder."""
        if not v or v.strip() == '':
            raise ValueError('api_key cannot be empty')
        if v == 'your-api-key-here':
            raise ValueError('api_key must be set to a valid key, not the placeholder value')
        return v.strip()


class ModelSettings(BaseModel):
    """Model configuration settings."""
    
    supported_models: List[str] = Field(
        default=[
            "glm-4.6v-flash",
            "gpt-oss-120b", 
            "grok-4",
            "gemini-2.5-flash"
        ],
        description="List of supported model IDs"
    )
    default_models: List[str] = Field(
        default=[
            "glm-4.6v-flash",
            "gpt-oss-120b",
            "grok-4", 
            "gemini-2.5-flash"
        ],
        description="List of default models to use for comparisons"
    )
    max_parallel_calls: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Maximum number of parallel API calls"
    )
    
    @validator('supported_models')
    def validate_supported_models(cls, v):
        """Validate that supported_models is not empty and contains valid model IDs."""
        if not v:
            raise ValueError('supported_models cannot be empty')
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError('supported_models cannot contain duplicates')
        
        # Validate model ID format (basic validation)
        for model_id in v:
            if not model_id or not isinstance(model_id, str):
                raise ValueError(f'Invalid model ID: {model_id}')
            if not model_id.strip():
                raise ValueError('Model IDs cannot be empty strings')
        
        return [model.strip() for model in v]
    
    @validator('default_models')
    def validate_default_models(cls, v, values):
        """Validate that default_models are subset of supported_models."""
        if not v:
            raise ValueError('default_models cannot be empty')
        
        supported = values.get('supported_models', [])
        if supported:
            invalid_models = [model for model in v if model not in supported]
            if invalid_models:
                raise ValueError(f'default_models contains unsupported models: {invalid_models}')
        
        return v


class LoggingSettings(BaseModel):
    """Logging configuration settings."""
    
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file: Optional[str] = Field(
        default="model_comparison.log",
        description="Log file path (optional)"
    )
    
    @validator('level')
    def validate_level(cls, v):
        """Validate that logging level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f'Invalid logging level: {v}. Must be one of {valid_levels}')
        return v_upper


class Config(BaseModel):
    """Main configuration model containing all settings."""
    
    api: ApiSettings = Field(
        default_factory=ApiSettings,
        description="API configuration settings"
    )
    models: ModelSettings = Field(
        default_factory=ModelSettings,
        description="Model configuration settings"
    )
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings,
        description="Logging configuration settings"
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = 'forbid'  # Forbid extra fields not defined in the model
        
    def validate_cross_field_constraints(self) -> List[str]:
        """Validate constraints that span multiple fields."""
        errors = []
        
        # Ensure max_parallel_calls doesn't exceed number of default models
        if self.models.max_parallel_calls > len(self.models.default_models):
            errors.append(
                f"max_parallel_calls ({self.models.max_parallel_calls}) cannot exceed "
                f"number of default_models ({len(self.models.default_models)})"
            )
        
        return errors