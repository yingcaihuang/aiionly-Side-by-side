"""
Unit tests for enhanced input validation and user feedback functionality.
Tests for task 7.1: Add input validation and user feedback
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from model_comparison_system.app_controller import AppController
from model_comparison_system.config.models import Config, ApiSettings, ModelSettings
from model_comparison_system.api.models import ModelResponse, ResponseStatus, ErrorInfo, ErrorType
from model_comparison_system.services.error_service import ErrorHandler


class TestEnhancedPromptValidation:
    """Test enhanced prompt validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config_service = Mock()
        self.mock_model_service = Mock()
        self.controller = AppController(self.mock_config_service, self.mock_model_service)
    
    def test_validate_prompt_none(self):
        """Test prompt validation with None input."""
        is_valid, error_msg = self.controller.validate_prompt(None)
        
        assert is_valid is False
        assert "cannot be empty" in error_msg
        assert "valid prompt to compare models" in error_msg
    
    def test_validate_prompt_empty_string(self):
        """Test prompt validation with empty string."""
        is_valid, error_msg = self.controller.validate_prompt("")
        
        assert is_valid is False
        assert "cannot be empty" in error_msg
        assert "valid prompt to compare models" in error_msg
    
    def test_validate_prompt_whitespace_only(self):
        """Test prompt validation with whitespace-only input."""
        test_cases = ["   ", "\n\n\n", "\t\t\t", "  \n\t  \n  "]
        
        for whitespace_prompt in test_cases:
            is_valid, error_msg = self.controller.validate_prompt(whitespace_prompt)
            
            assert is_valid is False
            assert "whitespace" in error_msg
            assert "meaningful prompt" in error_msg
    
    def test_validate_prompt_too_short(self):
        """Test prompt validation with too short input."""
        short_prompts = ["a", "ab", "  a  ", "  ab  "]
        
        for short_prompt in short_prompts:
            is_valid, error_msg = self.controller.validate_prompt(short_prompt)
            
            assert is_valid is False
            assert "too short" in error_msg
            assert "at least 3 characters" in error_msg
    
    def test_validate_prompt_too_long(self):
        """Test prompt validation with too long input."""
        long_prompt = "a" * 10001  # Exceeds 10,000 character limit
        is_valid, error_msg = self.controller.validate_prompt(long_prompt)
        
        assert is_valid is False
        assert "too long" in error_msg
        assert "10001 characters" in error_msg
        assert "10,000 characters or less" in error_msg
    
    def test_validate_prompt_null_characters(self):
        """Test prompt validation with null characters."""
        prompt_with_null = "This is a test\x00with null character"
        is_valid, error_msg = self.controller.validate_prompt(prompt_with_null)
        
        assert is_valid is False
        assert "invalid null characters" in error_msg
        assert "remove them" in error_msg
    
    def test_validate_prompt_excessive_repetition(self):
        """Test prompt validation with excessive character repetition."""
        # Create a prompt with 100+ repeated characters
        repetitive_prompt = "This is a test " + "a" * 100 + " end"
        is_valid, error_msg = self.controller.validate_prompt(repetitive_prompt)
        
        assert is_valid is False
        assert "excessive character repetition" in error_msg
        assert "more varied prompt" in error_msg
    
    def test_validate_prompt_too_many_lines(self):
        """Test prompt validation with too many lines."""
        # Create a prompt with 201 lines
        many_lines_prompt = "\n".join([f"Line {i}" for i in range(201)])
        is_valid, error_msg = self.controller.validate_prompt(many_lines_prompt)
        
        assert is_valid is False
        assert "too many lines" in error_msg
        assert "201" in error_msg
        assert "200 lines or less" in error_msg
    
    def test_validate_prompt_valid_cases(self):
        """Test prompt validation with valid inputs."""
        valid_prompts = [
            "Hello world",
            "This is a valid prompt for testing",
            "A" * 99 + "B" * 99 + "C" * 99,  # Varied characters, under repetition limit
            "Multi\nline\nprompt\nwith\nreasonable\nlength",
            "Prompt with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "   Valid prompt with leading/trailing spaces   ",
            "A reasonably long prompt that stays under the 10,000 character limit " * 50  # About 3,500 chars
        ]
        
        for valid_prompt in valid_prompts:
            is_valid, error_msg = self.controller.validate_prompt(valid_prompt)
            
            assert is_valid is True, f"Expected valid prompt to pass: {repr(valid_prompt[:50])}... Error: {error_msg}"
            assert error_msg == ""


class TestEnhancedErrorMessages:
    """Test enhanced user-friendly error messages."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    def test_authentication_error_message_enhanced(self):
        """Test enhanced authentication error message."""
        error_info = ErrorInfo(
            error_type=ErrorType.AUTHENTICATION_ERROR,
            message="401 Unauthorized",
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "Authentication failed for test-model" in message
        assert "config.yaml" in message
        assert "ensure it's valid" in message
    
    def test_network_error_message_enhanced(self):
        """Test enhanced network error message."""
        error_info = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            message="Connection failed",
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "Network connection failed for test-model" in message
        assert "internet connection" in message
        assert "temporarily unavailable" in message
    
    def test_timeout_error_message_enhanced(self):
        """Test enhanced timeout error message."""
        error_info = ErrorInfo(
            error_type=ErrorType.TIMEOUT_ERROR,
            message="Request timed out",
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "timed out after waiting for a response" in message
        assert "high load or temporary issues" in message
        assert "few moments" in message
    
    def test_rate_limit_error_message_enhanced(self):
        """Test enhanced rate limit error message."""
        error_info = ErrorInfo(
            error_type=ErrorType.RATE_LIMIT_ERROR,
            message="Too many requests",
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "Rate limit exceeded for test-model" in message
        assert "too many requests in a short time" in message
        assert "wait a moment" in message
    
    def test_validation_error_message_enhanced(self):
        """Test enhanced validation error message."""
        error_info = ErrorInfo(
            error_type=ErrorType.VALIDATION_ERROR,
            message="Invalid input",
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "Invalid request sent to test-model" in message
        assert "model's requirements" in message
    
    def test_configuration_error_message_enhanced(self):
        """Test enhanced configuration error message."""
        error_info = ErrorInfo(
            error_type=ErrorType.CONFIGURATION_ERROR,
            message="Config error",
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "Configuration error for test-model" in message
        assert "config.yaml file" in message
        assert "all settings are correct" in message
    
    def test_model_error_message_enhanced(self):
        """Test enhanced model error message."""
        error_info = ErrorInfo(
            error_type=ErrorType.MODEL_ERROR,
            message="Server error",
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "currently experiencing issues" in message
        assert "temporary problem" in message
        assert "contact support" in message
    
    def test_unknown_error_message_enhanced(self):
        """Test enhanced unknown error message."""
        error_info = ErrorInfo(
            error_type=ErrorType.UNKNOWN_ERROR,
            message="Unknown error",
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "unexpected error occurred" in message
        assert "configuration and network connection" in message
    
    def test_error_message_with_clean_details(self):
        """Test error message includes clean additional details."""
        error_info = ErrorInfo(
            error_type=ErrorType.MODEL_ERROR,
            message="Service temporarily unavailable",  # Clean, helpful message
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        assert "Service temporarily unavailable." in message
        assert "Additional details:" in message
    
    def test_error_message_filters_technical_details(self):
        """Test error message filters out technical details."""
        technical_messages = [
            "Traceback (most recent call last):",
            "Exception in line 42 of file main.py",
            "Error: ValueError at object 0x7f8b8c0d5040",
            "Stack trace: function call_model in module api",
            "Method handle_request in class ApiClient failed"
        ]
        
        for technical_msg in technical_messages:
            error_info = ErrorInfo(
                error_type=ErrorType.MODEL_ERROR,
                message=technical_msg,
                model_id="test-model"
            )
            
            message = self.error_handler.create_user_friendly_message(error_info)
            
            # Should not include the technical message
            assert technical_msg not in message
            assert "Additional details:" not in message
    
    def test_error_message_excludes_long_details(self):
        """Test error message excludes overly long details."""
        long_message = "A" * 200  # Very long message
        error_info = ErrorInfo(
            error_type=ErrorType.MODEL_ERROR,
            message=long_message,
            model_id="test-model"
        )
        
        message = self.error_handler.create_user_friendly_message(error_info)
        
        # Should not include the long message
        assert long_message not in message
        assert "Additional details:" not in message


class TestSubmitPromptValidation:
    """Test submit_prompt method with enhanced validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config_service = Mock()
        self.mock_model_service = Mock()
        self.controller = AppController(self.mock_config_service, self.mock_model_service)
        
        # Mock configuration
        self.mock_config = Config(
            api=ApiSettings(
                base_url="https://test.api.com",
                api_key="test-key",
                timeout=30
            ),
            models=ModelSettings(
                supported_models=["model1", "model2"],
                max_parallel_calls=2
            )
        )
        self.controller._current_config = self.mock_config
    
    @pytest.mark.asyncio
    async def test_submit_prompt_validation_failure(self):
        """Test submit_prompt with validation failure."""
        # Test with empty prompt
        result = await self.controller.submit_prompt("")
        
        assert result['success'] is False
        assert "cannot be empty" in result['error']
        assert result['responses'] == {}
        assert result['metadata'] == {}
    
    @pytest.mark.asyncio
    async def test_submit_prompt_validation_too_short(self):
        """Test submit_prompt with too short prompt."""
        result = await self.controller.submit_prompt("ab")
        
        assert result['success'] is False
        assert "too short" in result['error']
        assert "at least 3 characters" in result['error']
    
    @pytest.mark.asyncio
    async def test_submit_prompt_validation_too_long(self):
        """Test submit_prompt with too long prompt."""
        long_prompt = "a" * 10001
        result = await self.controller.submit_prompt(long_prompt)
        
        assert result['success'] is False
        assert "too long" in result['error']
        assert "10001 characters" in result['error']
    
    @pytest.mark.asyncio
    async def test_submit_prompt_configuration_error(self):
        """Test submit_prompt with configuration error."""
        # Clear current config to force validation
        self.controller._current_config = None
        
        # Mock configuration validation failure
        self.mock_config_service.load_config.side_effect = Exception("Config not found")
        
        result = await self.controller.submit_prompt("Valid prompt")
        
        assert result['success'] is False
        assert "Configuration error" in result['error']
        assert "Config not found" in result['error']


class TestErrorScenarioCoverage:
    """Test coverage of all error scenarios mentioned in requirements."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    def test_requirement_5_1_specific_error_messages(self):
        """Test Requirement 5.1: Display specific error message for each model."""
        # Test that each model gets its own specific error message
        models = ["model1", "model2", "model3"]
        
        for model_id in models:
            error_info = ErrorInfo(
                error_type=ErrorType.AUTHENTICATION_ERROR,
                message="Auth failed",
                model_id=model_id
            )
            
            message = self.error_handler.create_user_friendly_message(error_info)
            
            # Should contain the specific model ID
            assert model_id in message
            assert "Authentication failed" in message
    
    def test_requirement_5_2_network_timeout_messages(self):
        """Test Requirement 5.2: Show appropriate timeout messages for network issues."""
        network_timeout_scenarios = [
            (ErrorType.NETWORK_ERROR, "network connection"),
            (ErrorType.TIMEOUT_ERROR, "timed out")
        ]
        
        for error_type, expected_text in network_timeout_scenarios:
            error_info = ErrorInfo(
                error_type=error_type,
                message="Connection issue",
                model_id="test-model"
            )
            
            message = self.error_handler.create_user_friendly_message(error_info)
            
            assert expected_text in message.lower()
            assert "test-model" in message
    
    def test_requirement_5_3_empty_prompt_prevention(self):
        """Test Requirement 5.3: Prevent submission and show validation message for empty prompts."""
        controller = AppController(Mock(), Mock())
        
        empty_prompt_cases = [None, "", "   ", "\n\n", "\t\t"]
        
        for empty_prompt in empty_prompt_cases:
            is_valid, error_msg = controller.validate_prompt(empty_prompt)
            
            # Should prevent submission
            assert is_valid is False
            
            # Should show validation message
            assert len(error_msg) > 0
            assert any(keyword in error_msg.lower() for keyword in ["empty", "cannot", "please"])