"""
Unit tests for the AppController class.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from model_comparison_system.app_controller import AppController
from model_comparison_system.config.models import Config, ApiSettings, ModelSettings
from model_comparison_system.api.models import ModelResponse, ResponseStatus


class TestAppController:
    """Test cases for AppController."""
    
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
    
    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        self.mock_config_service.load_config.return_value = self.mock_config
        self.mock_config_service.validate_config.return_value = []
        
        is_valid, errors = self.controller.validate_configuration()
        
        assert is_valid is True
        assert errors == []
        assert self.controller._current_config == self.mock_config
    
    def test_validate_configuration_failure(self):
        """Test configuration validation failure."""
        error_messages = ["Invalid API key", "Missing model configuration"]
        self.mock_config_service.load_config.return_value = self.mock_config
        self.mock_config_service.validate_config.return_value = error_messages
        
        is_valid, errors = self.controller.validate_configuration()
        
        assert is_valid is False
        assert errors == error_messages
    
    def test_validate_prompt_empty(self):
        """Test prompt validation with empty prompt."""
        is_valid, error_msg = self.controller.validate_prompt("")
        
        assert is_valid is False
        assert "empty" in error_msg.lower()
    
    def test_validate_prompt_whitespace_only(self):
        """Test prompt validation with whitespace-only prompt."""
        is_valid, error_msg = self.controller.validate_prompt("   \n\t  ")
        
        assert is_valid is False
        assert "empty" in error_msg.lower()
    
    def test_validate_prompt_too_long(self):
        """Test prompt validation with overly long prompt."""
        long_prompt = "a" * 10001  # Exceeds 10,000 character limit
        is_valid, error_msg = self.controller.validate_prompt(long_prompt)
        
        assert is_valid is False
        assert "too long" in error_msg.lower()
    
    def test_validate_prompt_valid(self):
        """Test prompt validation with valid prompt."""
        is_valid, error_msg = self.controller.validate_prompt("This is a valid prompt")
        
        assert is_valid is True
        assert error_msg == ""
    
    @pytest.mark.asyncio
    async def test_submit_prompt_success(self):
        """Test successful prompt submission."""
        # Setup mocks
        self.controller._current_config = self.mock_config
        
        mock_responses = {
            "model1": ModelResponse(
                model_id="model1",
                content="Response from model 1",
                status=ResponseStatus.SUCCESS,
                duration=1.5
            ),
            "model2": ModelResponse(
                model_id="model2",
                content="Response from model 2",
                status=ResponseStatus.SUCCESS,
                duration=2.0
            )
        }
        
        self.mock_model_service.compare_models = AsyncMock(return_value=mock_responses)
        
        # Test
        result = await self.controller.submit_prompt("Test prompt")
        
        # Assertions
        assert result['success'] is True
        assert result['error'] is None
        assert len(result['responses']) == 2
        assert result['metadata']['success_count'] == 2
        assert result['metadata']['error_count'] == 0
        assert result['metadata']['prompt'] == "Test prompt"
    
    @pytest.mark.asyncio
    async def test_submit_prompt_invalid_prompt(self):
        """Test prompt submission with invalid prompt."""
        result = await self.controller.submit_prompt("")
        
        assert result['success'] is False
        assert "empty" in result['error'].lower()
        assert result['responses'] == {}
    
    @pytest.mark.asyncio
    async def test_submit_prompt_no_config(self):
        """Test prompt submission without loaded configuration."""
        # Mock configuration validation failure
        self.mock_config_service.load_config.side_effect = Exception("Config not found")
        
        result = await self.controller.submit_prompt("Test prompt")
        
        assert result['success'] is False
        assert "configuration error" in result['error'].lower()
    
    def test_get_model_status_no_config(self):
        """Test getting model status without loaded configuration."""
        status = self.controller.get_model_status()
        
        assert status == {}
    
    def test_get_model_status_with_config(self):
        """Test getting model status with loaded configuration."""
        self.controller._current_config = self.mock_config
        
        status = self.controller.get_model_status()
        
        assert len(status) == 2
        assert status["model1"] == "available"
        assert status["model2"] == "available"
    
    def test_get_supported_models(self):
        """Test getting supported models."""
        expected_models = ["model1", "model2", "model3"]
        self.mock_model_service.get_supported_models.return_value = expected_models
        
        models = self.controller.get_supported_models()
        
        assert models == expected_models
    
    def test_get_configuration_info_no_config(self):
        """Test getting configuration info without loaded config."""
        info = self.controller.get_configuration_info()
        
        assert info == {'loaded': False}
    
    def test_get_configuration_info_with_config(self):
        """Test getting configuration info with loaded config."""
        self.controller._current_config = self.mock_config
        
        info = self.controller.get_configuration_info()
        
        assert info['loaded'] is True
        assert info['api_base_url'] == "https://test.api.com"
        assert info['supported_models'] == ["model1", "model2"]
        assert info['max_parallel_calls'] == 2
        assert info['timeout'] == 30