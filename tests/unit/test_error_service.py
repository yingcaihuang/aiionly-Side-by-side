"""Unit tests for ErrorHandler class."""

import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from model_comparison_system.services.error_service import (
    ErrorHandler, 
    RetryStrategy, 
    RetryConfig
)
from model_comparison_system.api.models import (
    ErrorInfo,
    ErrorType,
    ModelResponse,
    ResponseStatus
)


@pytest.fixture
def error_handler():
    """Create ErrorHandler instance for testing."""
    return ErrorHandler()


@pytest.fixture
def mock_logger():
    """Create mock logger for testing."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def error_handler_with_mock_logger(mock_logger):
    """Create ErrorHandler with mock logger."""
    return ErrorHandler(logger=mock_logger)


class TestErrorHandlerInitialization:
    """Test ErrorHandler initialization."""
    
    def test_init_with_default_logger(self):
        """Test initialization with default logger."""
        handler = ErrorHandler()
        
        assert handler.logger is not None
        assert isinstance(handler.retry_configs, dict)
        assert len(handler.retry_configs) > 0
    
    def test_init_with_custom_logger(self, mock_logger):
        """Test initialization with custom logger."""
        handler = ErrorHandler(logger=mock_logger)
        
        assert handler.logger == mock_logger
    
    def test_init_sets_retry_configs(self, error_handler):
        """Test that initialization sets up retry configurations."""
        configs = error_handler.retry_configs
        
        # Check that all error types have configurations
        expected_types = [
            ErrorType.RATE_LIMIT_ERROR,
            ErrorType.NETWORK_ERROR,
            ErrorType.TIMEOUT_ERROR,
            ErrorType.MODEL_ERROR,
            ErrorType.AUTHENTICATION_ERROR,
            ErrorType.VALIDATION_ERROR,
            ErrorType.CONFIGURATION_ERROR
        ]
        
        for error_type in expected_types:
            assert error_type in configs
            assert isinstance(configs[error_type], RetryConfig)


class TestErrorClassification:
    """Test error classification functionality."""
    
    def test_classify_network_errors(self, error_handler):
        """Test classification of network-related errors."""
        network_errors = [
            Exception("Network connection failed"),
            Exception("DNS resolution error"),
            ConnectionError("Connection refused"),
            Exception("connection timeout")
        ]
        
        for error in network_errors:
            assert error_handler.classify_error(error) == ErrorType.NETWORK_ERROR
    
    def test_classify_timeout_errors(self, error_handler):
        """Test classification of timeout errors."""
        timeout_errors = [
            Exception("Request timeout"),
            asyncio.TimeoutError("Operation timed out"),
            Exception("timeout occurred")
        ]
        
        for error in timeout_errors:
            assert error_handler.classify_error(error) == ErrorType.TIMEOUT_ERROR
    
    def test_classify_authentication_errors(self, error_handler):
        """Test classification of authentication errors."""
        auth_errors = [
            Exception("Authentication failed"),
            Exception("401 Unauthorized"),
            Exception("403 Forbidden"),
            Exception("Invalid auth token")
        ]
        
        for error in auth_errors:
            assert error_handler.classify_error(error) == ErrorType.AUTHENTICATION_ERROR
    
    def test_classify_rate_limit_errors(self, error_handler):
        """Test classification of rate limit errors."""
        rate_limit_errors = [
            Exception("Rate limit exceeded"),
            Exception("Too many requests"),
            Exception("429 error")
        ]
        
        for error in rate_limit_errors:
            assert error_handler.classify_error(error) == ErrorType.RATE_LIMIT_ERROR
    
    def test_classify_validation_errors(self, error_handler):
        """Test classification of validation errors."""
        validation_errors = [
            Exception("Validation failed"),
            Exception("Invalid input"),
            Exception("400 Bad Request")
        ]
        
        for error in validation_errors:
            assert error_handler.classify_error(error) == ErrorType.VALIDATION_ERROR
    
    def test_classify_model_errors(self, error_handler):
        """Test classification of model/server errors."""
        model_errors = [
            Exception("500 Internal Server Error"),
            Exception("502 Bad Gateway"),
            Exception("503 Service Unavailable"),
            Exception("504 Gateway Timeout")
        ]
        
        for error in model_errors:
            assert error_handler.classify_error(error) == ErrorType.MODEL_ERROR
    
    def test_classify_unknown_errors(self, error_handler):
        """Test classification of unknown errors."""
        unknown_errors = [
            Exception("Some random error"),
            ValueError("Unexpected value"),
            RuntimeError("Runtime issue")
        ]
        
        for error in unknown_errors:
            assert error_handler.classify_error(error) == ErrorType.UNKNOWN_ERROR


class TestUserFriendlyMessages:
    """Test user-friendly message generation."""
    
    def test_authentication_error_message(self, error_handler):
        """Test user-friendly message for authentication errors."""
        error_info = ErrorInfo(
            error_type=ErrorType.AUTHENTICATION_ERROR,
            message="401 Unauthorized",
            model_id="test-model"
        )
        
        message = error_handler.create_user_friendly_message(error_info)
        
        assert "Authentication failed" in message
        assert "test-model" in message
        assert "API key" in message
    
    def test_network_error_message(self, error_handler):
        """Test user-friendly message for network errors."""
        error_info = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            message="Connection failed",
            model_id="test-model"
        )
        
        message = error_handler.create_user_friendly_message(error_info)
        
        assert "Network connection failed" in message
        assert "test-model" in message
        assert "internet connection" in message
    
    def test_timeout_error_message(self, error_handler):
        """Test user-friendly message for timeout errors."""
        error_info = ErrorInfo(
            error_type=ErrorType.TIMEOUT_ERROR,
            message="Request timed out",
            model_id="test-model"
        )
        
        message = error_handler.create_user_friendly_message(error_info)
        
        assert "timed out" in message
        assert "test-model" in message
        assert "high load" in message
    
    def test_rate_limit_error_message(self, error_handler):
        """Test user-friendly message for rate limit errors."""
        error_info = ErrorInfo(
            error_type=ErrorType.RATE_LIMIT_ERROR,
            message="Too many requests",
            model_id="test-model"
        )
        
        message = error_handler.create_user_friendly_message(error_info)
        
        assert "Rate limit exceeded" in message
        assert "test-model" in message
        assert "wait a moment" in message
    
    def test_message_includes_short_details(self, error_handler):
        """Test that short error details are included in user message."""
        error_info = ErrorInfo(
            error_type=ErrorType.MODEL_ERROR,
            message="Model overloaded",  # Short, helpful message
            model_id="test-model"
        )
        
        message = error_handler.create_user_friendly_message(error_info)
        
        assert "Model overloaded" in message
    
    def test_message_excludes_long_details(self, error_handler):
        """Test that long error details are excluded from user message."""
        long_message = "A" * 150  # Very long message
        error_info = ErrorInfo(
            error_type=ErrorType.MODEL_ERROR,
            message=long_message,
            model_id="test-model"
        )
        
        message = error_handler.create_user_friendly_message(error_info)
        
        assert long_message not in message
    
    def test_message_excludes_technical_details(self, error_handler):
        """Test that technical details are excluded from user message."""
        error_info = ErrorInfo(
            error_type=ErrorType.MODEL_ERROR,
            message="Traceback: Exception in line 42",
            model_id="test-model"
        )
        
        message = error_handler.create_user_friendly_message(error_info)
        
        assert "Traceback" not in message


class TestRetryDelayCalculation:
    """Test retry delay calculation."""
    
    def test_no_retry_strategy(self, error_handler):
        """Test no retry strategy returns zero delay."""
        config = RetryConfig(
            strategy=RetryStrategy.NO_RETRY,
            max_retries=0
        )
        
        delay = error_handler._calculate_delay(0, config)
        assert delay == 0.0
    
    def test_immediate_retry_strategy(self, error_handler):
        """Test immediate retry strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.IMMEDIATE_RETRY,
            max_retries=3,
            base_delay=0.5
        )
        
        delay = error_handler._calculate_delay(0, config)
        assert delay == 0.5
        
        delay = error_handler._calculate_delay(2, config)
        assert delay == 0.5
    
    def test_linear_backoff_strategy(self, error_handler):
        """Test linear backoff strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            max_retries=3,
            base_delay=1.0,
            jitter=False  # Disable jitter for predictable testing
        )
        
        assert error_handler._calculate_delay(0, config) == 1.0  # 1 * 1
        assert error_handler._calculate_delay(1, config) == 2.0  # 1 * 2
        assert error_handler._calculate_delay(2, config) == 3.0  # 1 * 3
    
    def test_exponential_backoff_strategy(self, error_handler):
        """Test exponential backoff strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=3,
            base_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False  # Disable jitter for predictable testing
        )
        
        assert error_handler._calculate_delay(0, config) == 1.0  # 1 * 2^0
        assert error_handler._calculate_delay(1, config) == 2.0  # 1 * 2^1
        assert error_handler._calculate_delay(2, config) == 4.0  # 1 * 2^2
    
    def test_max_delay_limit(self, error_handler):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=10,
            base_delay=1.0,
            max_delay=5.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        
        # Large attempt number should be capped
        delay = error_handler._calculate_delay(10, config)
        assert delay == 5.0
    
    def test_jitter_adds_randomness(self, error_handler):
        """Test that jitter adds randomness to delay."""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            max_retries=3,
            base_delay=10.0,
            jitter=True
        )
        
        # Run multiple times to check for variation
        delays = [error_handler._calculate_delay(1, config) for _ in range(10)]
        
        # Should have some variation due to jitter
        assert len(set(delays)) > 1  # Not all delays should be identical
        
        # All delays should be reasonably close to expected value (20.0)
        for delay in delays:
            assert 18.0 <= delay <= 22.0  # Within 10% jitter range


@pytest.mark.asyncio
class TestModelErrorHandling:
    """Test model error handling functionality."""
    
    async def test_handle_model_error_without_retry(self, error_handler):
        """Test handling model error without retry function."""
        error = Exception("Test error")
        
        result = await error_handler.handle_model_error(
            error, 
            "test-model"
        )
        
        assert isinstance(result, ModelResponse)
        assert result.model_id == "test-model"
        assert result.status == ResponseStatus.ERROR
        assert result.error_message is not None
        assert result.content == ""
    
    async def test_handle_model_error_with_successful_retry(self, error_handler):
        """Test handling model error with successful retry."""
        error = Exception("Rate limit exceeded")  # This should trigger retry
        
        # Mock operation that succeeds on retry
        success_response = ModelResponse(
            model_id="test-model",
            content="Success after retry",
            duration=1.0,
            status=ResponseStatus.SUCCESS
        )
        
        retry_func = AsyncMock(return_value=success_response)
        
        result = await error_handler.handle_model_error(
            error,
            "test-model", 
            operation_func=retry_func
        )
        
        assert result == success_response
        assert retry_func.called
    
    async def test_handle_model_error_with_failed_retry(self, error_handler):
        """Test handling model error when retry fails."""
        error = Exception("Rate limit exceeded")
        
        # Mock operation that always fails
        retry_func = AsyncMock(side_effect=Exception("Still failing"))
        
        result = await error_handler.handle_model_error(
            error,
            "test-model",
            operation_func=retry_func
        )
        
        assert isinstance(result, ModelResponse)
        assert result.status == ResponseStatus.ERROR
        assert result.model_id == "test-model"
    
    async def test_handle_model_error_no_retry_for_auth_error(self, error_handler):
        """Test that authentication errors are not retried."""
        error = Exception("401 Unauthorized")
        
        retry_func = AsyncMock()
        
        result = await error_handler.handle_model_error(
            error,
            "test-model",
            operation_func=retry_func
        )
        
        # Should not have called retry function
        assert not retry_func.called
        assert result.status == ResponseStatus.ERROR


class TestApiInteractionLogging:
    """Test API interaction logging functionality."""
    
    def test_log_successful_interaction(self, error_handler_with_mock_logger, mock_logger):
        """Test logging successful API interaction."""
        response = ModelResponse(
            model_id="test-model",
            content="Test response content",
            duration=1.5,
            status=ResponseStatus.SUCCESS
        )
        
        error_handler_with_mock_logger.log_api_interaction(
            model_id="test-model",
            prompt="Test prompt",
            response=response,
            duration=1.5
        )
        
        # Verify info log was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "API call successful" in log_call
        assert "test-model" in log_call
    
    def test_log_failed_interaction(self, error_handler_with_mock_logger, mock_logger):
        """Test logging failed API interaction."""
        error = Exception("API call failed")
        
        error_handler_with_mock_logger.log_api_interaction(
            model_id="test-model",
            prompt="Test prompt",
            error=error,
            duration=0.5
        )
        
        # Verify error log was called
        mock_logger.error.assert_called_once()
        log_call = mock_logger.error.call_args[0][0]
        assert "API call failed" in log_call
        assert "test-model" in log_call
    
    def test_log_interaction_with_long_content(self, error_handler_with_mock_logger, mock_logger):
        """Test logging with long prompt and response content."""
        long_content = "A" * 200  # Long content
        
        response = ModelResponse(
            model_id="test-model",
            content=long_content,
            duration=1.0,
            status=ResponseStatus.SUCCESS
        )
        
        error_handler_with_mock_logger.log_api_interaction(
            model_id="test-model",
            prompt=long_content,
            response=response
        )
        
        # Verify content was truncated in log
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "..." in log_call  # Should contain truncation indicator
    
    def test_log_interaction_with_additional_info(self, error_handler_with_mock_logger, mock_logger):
        """Test logging with additional information."""
        response = ModelResponse(
            model_id="test-model",
            content="Response",
            duration=1.0,
            status=ResponseStatus.SUCCESS
        )
        
        additional_info = {
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        error_handler_with_mock_logger.log_api_interaction(
            model_id="test-model",
            prompt="Test prompt",
            response=response,
            additional_info=additional_info
        )
        
        # Verify additional info was included
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "temperature" in log_call
        assert "max_tokens" in log_call


class TestRetryConfig:
    """Test RetryConfig dataclass."""
    
    def test_retry_config_creation(self):
        """Test creating RetryConfig with various parameters."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            backoff_multiplier=1.5,
            jitter=False
        )
        
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 30.0
        assert config.backoff_multiplier == 1.5
        assert config.jitter is False
    
    def test_retry_config_defaults(self):
        """Test RetryConfig default values."""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            max_retries=3
        )
        
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True