"""Error handling and logging service for centralized error management."""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass

from ..api.models import ErrorInfo, ErrorType, ModelResponse, ResponseStatus


T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry strategy enumeration."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE_RETRY = "immediate_retry"
    NO_RETRY = "no_retry"


@dataclass
class RetryConfig:
    """Configuration for retry strategies."""
    strategy: RetryStrategy
    max_retries: int
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


class ErrorHandler:
    """Centralized error handling and logging service with retry strategies."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize ErrorHandler with optional logger.
        
        Args:
            logger: Logger instance (creates default if not provided)
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Default retry configurations for different error types
        self.retry_configs = {
            ErrorType.RATE_LIMIT_ERROR: RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=5,
                base_delay=2.0,
                max_delay=60.0
            ),
            ErrorType.NETWORK_ERROR: RetryConfig(
                strategy=RetryStrategy.LINEAR_BACKOFF,
                max_retries=3,
                base_delay=1.0,
                max_delay=10.0
            ),
            ErrorType.TIMEOUT_ERROR: RetryConfig(
                strategy=RetryStrategy.IMMEDIATE_RETRY,
                max_retries=2,
                base_delay=0.5
            ),
            ErrorType.MODEL_ERROR: RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=2,
                base_delay=1.0,
                max_delay=5.0
            ),
            ErrorType.AUTHENTICATION_ERROR: RetryConfig(
                strategy=RetryStrategy.NO_RETRY,
                max_retries=0
            ),
            ErrorType.VALIDATION_ERROR: RetryConfig(
                strategy=RetryStrategy.NO_RETRY,
                max_retries=0
            ),
            ErrorType.CONFIGURATION_ERROR: RetryConfig(
                strategy=RetryStrategy.NO_RETRY,
                max_retries=0
            )
        }
        
        self.logger.info("ErrorHandler initialized with retry strategies")
    
    async def handle_model_error(
        self,
        error: Exception,
        model_id: str,
        operation_func: Optional[Callable[[], Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """Handle model-specific errors with retry logic.
        
        Args:
            error: Exception that occurred
            model_id: ID of the model that failed
            operation_func: Function to retry (optional)
            context: Additional context information
            
        Returns:
            ModelResponse with error information or successful retry result
        """
        error_type = self.classify_error(error)
        error_info = self._create_error_info(error_type, str(error), model_id, context)
        
        # Log the error
        self._log_error(error_info, error)
        
        # Attempt retry if configured and operation function provided
        if operation_func and error_type in self.retry_configs:
            retry_config = self.retry_configs[error_type]
            
            if retry_config.max_retries > 0:
                self.logger.info(
                    f"Attempting retry for model {model_id}, error type: {error_type.value}"
                )
                
                retry_result = await self._retry_with_strategy(
                    operation_func,
                    retry_config,
                    model_id,
                    error_type
                )
                
                if retry_result is not None:
                    return retry_result
        
        # Create error response if no retry or retry failed
        return self._create_error_response(error_info, model_id)
    
    def classify_error(self, error: Exception) -> ErrorType:
        """Classify an exception into an ErrorType.
        
        Args:
            error: Exception to classify
            
        Returns:
            Appropriate ErrorType
        """
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Network-related errors
        if any(keyword in error_str for keyword in ['network', 'connection', 'dns', 'resolve']):
            return ErrorType.NETWORK_ERROR
        
        if any(keyword in error_type_name for keyword in ['connection', 'network', 'dns']):
            return ErrorType.NETWORK_ERROR
        
        # Authentication errors
        if any(keyword in error_str for keyword in ['auth', 'unauthorized', '401', 'forbidden', '403']):
            return ErrorType.AUTHENTICATION_ERROR
        
        # Rate limiting
        if any(keyword in error_str for keyword in ['rate limit', 'too many requests', '429']):
            return ErrorType.RATE_LIMIT_ERROR
        
        # Validation errors
        if any(keyword in error_str for keyword in ['validation', 'invalid', 'bad request', '400']):
            return ErrorType.VALIDATION_ERROR
        
        # Configuration errors
        if any(keyword in error_str for keyword in ['config', 'configuration', 'setting']):
            return ErrorType.CONFIGURATION_ERROR
        
        # Model-specific errors (5xx server errors) - check before timeout to catch "504 Gateway Timeout"
        if any(keyword in error_str for keyword in ['500', '502', '503', '504', 'server error']):
            return ErrorType.MODEL_ERROR
        
        # Timeout errors (check after model errors to avoid catching "504 Gateway Timeout" as timeout)
        if 'timeout' in error_str or 'timeout' in error_type_name:
            return ErrorType.TIMEOUT_ERROR
        
        if isinstance(error, asyncio.TimeoutError):
            return ErrorType.TIMEOUT_ERROR
        
        # Default to unknown error
        return ErrorType.UNKNOWN_ERROR
    
    def create_user_friendly_message(self, error_info: ErrorInfo) -> str:
            """Convert technical error information to user-friendly messages.

            Args:
                error_info: Error information to convert

            Returns:
                User-friendly error message
            """
            error_type = error_info.error_type
            model_id = error_info.model_id or "unknown model"

            # Base messages for each error type with more specific guidance
            messages = {
                ErrorType.AUTHENTICATION_ERROR: (
                    f"Authentication failed for {model_id}. "
                    f"Please check your API key configuration in config.yaml and ensure it's valid."
                ),
                ErrorType.NETWORK_ERROR: (
                    f"Network connection failed for {model_id}. "
                    f"Please check your internet connection and try again. "
                    f"If the problem persists, the model service may be temporarily unavailable."
                ),
                ErrorType.TIMEOUT_ERROR: (
                    f"Request to {model_id} timed out after waiting for a response. "
                    f"The model may be experiencing high load or temporary issues. "
                    f"Please try again in a few moments."
                ),
                ErrorType.RATE_LIMIT_ERROR: (
                    f"Rate limit exceeded for {model_id}. "
                    f"You've made too many requests in a short time. "
                    f"Please wait a moment before trying again."
                ),
                ErrorType.VALIDATION_ERROR: (
                    f"Invalid request sent to {model_id}. "
                    f"Please check your prompt and ensure it meets the model's requirements."
                ),
                ErrorType.CONFIGURATION_ERROR: (
                    f"Configuration error for {model_id}. "
                    f"Please check your config.yaml file and ensure all settings are correct."
                ),
                ErrorType.MODEL_ERROR: (
                    f"Model {model_id} is currently experiencing issues. "
                    f"This is likely a temporary problem with the model service. "
                    f"Please try again later or contact support if the issue persists."
                ),
                ErrorType.UNKNOWN_ERROR: (
                    f"An unexpected error occurred with {model_id}. "
                    f"Please try again, and if the problem continues, check your configuration and network connection."
                )
            }

            base_message = messages.get(error_type, messages[ErrorType.UNKNOWN_ERROR])

            # Add specific error details if available and helpful
            if error_info.message and len(error_info.message) < 150:
                # Only include short, potentially helpful error messages
                # Filter out technical jargon and stack traces
                if not any(keyword in error_info.message.lower() for keyword in [
                    'traceback', 'exception', 'error:', 'stack trace', 'line ', 'file "',
                    'module ', 'function ', 'method ', 'class ', 'object at 0x'
                ]):
                    # Clean up the message
                    clean_message = error_info.message.strip()
                    if clean_message and not clean_message.endswith('.'):
                        clean_message += '.'
                    base_message += f" Additional details: {clean_message}"

            return base_message

    
    def log_api_interaction(
        self,
        model_id: str,
        prompt: str,
        response: Optional[ModelResponse] = None,
        error: Optional[Exception] = None,
        duration: Optional[float] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log API interactions for debugging purposes.
        
        Args:
            model_id: ID of the model
            prompt: Prompt sent to the model
            response: Response received (if any)
            error: Error that occurred (if any)
            duration: Request duration in seconds
            additional_info: Additional information to log
        """
        # Prepare log data
        log_data = {
            'model_id': model_id,
            'prompt_length': len(prompt) if prompt else 0,
            'prompt_preview': prompt[:100] + '...' if prompt and len(prompt) > 100 else prompt,
            'duration': duration,
            'timestamp': time.time()
        }
        
        if additional_info:
            log_data.update(additional_info)
        
        # Log based on outcome
        if error:
            error_type = self.classify_error(error)
            log_data.update({
                'status': 'error',
                'error_type': error_type.value,
                'error_message': str(error)
            })
            self.logger.error(f"API call failed: {log_data}")
            
        elif response:
            log_data.update({
                'status': response.status.value,
                'response_length': len(response.content) if response.content else 0,
                'response_preview': (
                    response.content[:100] + '...' 
                    if response.content and len(response.content) > 100 
                    else response.content
                )
            })
            
            if response.is_success:
                self.logger.info(f"API call successful: {log_data}")
            else:
                self.logger.warning(f"API call failed: {log_data}")
        else:
            log_data['status'] = 'unknown'
            self.logger.warning(f"API call completed with unknown status: {log_data}")
    
    async def _retry_with_strategy(
        self,
        operation_func: Callable[[], Any],
        retry_config: RetryConfig,
        model_id: str,
        error_type: ErrorType
    ) -> Optional[ModelResponse]:
        """Retry an operation using the specified strategy.
        
        Args:
            operation_func: Function to retry
            retry_config: Retry configuration
            model_id: Model ID for logging
            error_type: Type of error that triggered retry
            
        Returns:
            Successful ModelResponse or None if all retries failed
        """
        for attempt in range(retry_config.max_retries):
            try:
                # Calculate delay
                delay = self._calculate_delay(attempt, retry_config)
                
                if delay > 0:
                    self.logger.debug(
                        f"Retrying {model_id} in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{retry_config.max_retries})"
                    )
                    await asyncio.sleep(delay)
                
                # Attempt the operation
                result = await operation_func()
                
                # If we get a ModelResponse, check if it's successful
                if isinstance(result, ModelResponse):
                    if result.is_success:
                        self.logger.info(
                            f"Retry successful for {model_id} on attempt {attempt + 1}"
                        )
                        return result
                    else:
                        # If it's still an error, continue retrying
                        continue
                else:
                    # For other return types, assume success
                    self.logger.info(
                        f"Retry successful for {model_id} on attempt {attempt + 1}"
                    )
                    return result
                    
            except Exception as retry_error:
                self.logger.warning(
                    f"Retry attempt {attempt + 1} failed for {model_id}: {retry_error}"
                )
                
                # If this is the last attempt, don't continue
                if attempt == retry_config.max_retries - 1:
                    break
        
        self.logger.error(f"All retry attempts failed for {model_id}")
        return None
    
    def _calculate_delay(self, attempt: int, retry_config: RetryConfig) -> float:
        """Calculate delay for retry attempt based on strategy.
        
        Args:
            attempt: Current attempt number (0-based)
            retry_config: Retry configuration
            
        Returns:
            Delay in seconds
        """
        if retry_config.strategy == RetryStrategy.NO_RETRY:
            return 0.0
        
        elif retry_config.strategy == RetryStrategy.IMMEDIATE_RETRY:
            return retry_config.base_delay
        
        elif retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = retry_config.base_delay * (attempt + 1)
        
        elif retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = retry_config.base_delay * (retry_config.backoff_multiplier ** attempt)
        
        else:
            delay = retry_config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, retry_config.max_delay)
        
        # Add jitter if enabled
        if retry_config.jitter and delay > 0:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def _create_error_info(
        self,
        error_type: ErrorType,
        message: str,
        model_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorInfo:
        """Create ErrorInfo object from error details.
        
        Args:
            error_type: Type of error
            message: Error message
            model_id: Model ID (optional)
            context: Additional context (optional)
            
        Returns:
            ErrorInfo object
        """
        return ErrorInfo(
            error_type=error_type,
            message=message,
            model_id=model_id,
            details=context
        )
    
    def _create_error_response(
        self,
        error_info: ErrorInfo,
        model_id: str
    ) -> ModelResponse:
        """Create ModelResponse for error cases.
        
        Args:
            error_info: Error information
            model_id: Model ID
            
        Returns:
            ModelResponse with error information
        """
        user_message = self.create_user_friendly_message(error_info)
        
        return ModelResponse(
            model_id=model_id,
            content="",
            duration=0.0,
            status=ResponseStatus.ERROR,
            error_message=user_message,
            error_info=error_info
        )
    
    def _log_error(
        self,
        error_info: ErrorInfo,
        original_error: Exception
    ) -> None:
        """Log error information with appropriate level.
        
        Args:
            error_info: Error information to log
            original_error: Original exception
        """
        log_data = {
            'error_type': error_info.error_type.value,
            'model_id': error_info.model_id,
            'message': error_info.message,
            'timestamp': error_info.timestamp.isoformat()
        }
        
        if error_info.details:
            log_data['details'] = error_info.details
        
        # Log with appropriate level based on error type
        if error_info.error_type in [ErrorType.AUTHENTICATION_ERROR, ErrorType.CONFIGURATION_ERROR]:
            self.logger.error(f"Critical error: {log_data}")
        elif error_info.error_type in [ErrorType.RATE_LIMIT_ERROR, ErrorType.TIMEOUT_ERROR]:
            self.logger.warning(f"Retryable error: {log_data}")
        else:
            self.logger.error(f"Error occurred: {log_data}")
        
        # Log exception details at debug level
        self.logger.debug(f"Exception details for {error_info.model_id}: {original_error}", exc_info=True)