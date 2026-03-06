"""API client data models for MAAS API integration."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ResponseStatus(str, Enum):
    """Response status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class ErrorType(str, Enum):
    """Error type enumeration for categorizing different error conditions."""
    AUTHENTICATION_ERROR = "auth_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "config_error"
    MODEL_ERROR = "model_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorInfo(BaseModel):
    """Error information model for detailed error reporting."""
    
    error_type: ErrorType = Field(
        ...,
        description="Type of error that occurred"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    model_id: Optional[str] = Field(
        default=None,
        description="Model ID associated with the error (if applicable)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the error occurred"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class ModelResponse(BaseModel):
    """Response model for individual model API calls."""
    
    model_id: str = Field(
        ...,
        description="ID of the model that generated this response"
    )
    content: str = Field(
        default="",
        description="Generated content from the model"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the response was received"
    )
    duration: float = Field(
        default=0.0,
        ge=0.0,
        description="Response time in seconds"
    )
    status: ResponseStatus = Field(
        ...,
        description="Status of the response"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if status is ERROR"
    )
    error_info: Optional[ErrorInfo] = Field(
        default=None,
        description="Detailed error information if available"
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
    
    @property
    def is_success(self) -> bool:
        """Check if the response was successful."""
        return self.status == ResponseStatus.SUCCESS
    
    @property
    def is_error(self) -> bool:
        """Check if the response had an error."""
        return self.status == ResponseStatus.ERROR


class ApiResponse(BaseModel):
    """Generic API response model for MAAS API calls."""
    
    success: bool = Field(
        ...,
        description="Whether the API call was successful"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Response data from the API"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the call failed"
    )
    status_code: int = Field(
        ...,
        description="HTTP status code"
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Response headers"
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if the response indicates rate limiting."""
        return self.status_code == 429
    
    @property
    def is_authentication_error(self) -> bool:
        """Check if the response indicates authentication error."""
        return self.status_code == 401


class ComparisonResult(BaseModel):
    """Result model for multi-model comparison operations."""
    
    prompt: str = Field(
        ...,
        description="The prompt that was sent to all models"
    )
    responses: Dict[str, ModelResponse] = Field(
        default_factory=dict,
        description="Responses from each model, keyed by model_id"
    )
    total_duration: float = Field(
        default=0.0,
        ge=0.0,
        description="Total time taken for all model calls"
    )
    success_count: int = Field(
        default=0,
        ge=0,
        description="Number of successful model responses"
    )
    error_count: int = Field(
        default=0,
        ge=0,
        description="Number of failed model responses"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the comparison was initiated"
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
    
    @property
    def total_models(self) -> int:
        """Total number of models in the comparison."""
        return len(self.responses)
    
    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total_models == 0:
            return 0.0
        return (self.success_count / self.total_models) * 100.0
    
    def get_successful_responses(self) -> Dict[str, ModelResponse]:
        """Get only the successful responses."""
        return {
            model_id: response 
            for model_id, response in self.responses.items() 
            if response.is_success
        }
    
    def get_failed_responses(self) -> Dict[str, ModelResponse]:
        """Get only the failed responses."""
        return {
            model_id: response 
            for model_id, response in self.responses.items() 
            if response.is_error
        }