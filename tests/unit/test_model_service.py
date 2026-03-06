"""Unit tests for ModelService class."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from model_comparison_system.services.model_service import ModelService
from model_comparison_system.api.models import (
    ModelResponse, 
    ResponseStatus, 
    ComparisonResult,
    ErrorType,
    ErrorInfo
)
from model_comparison_system.config.models import Config, ApiSettings, ModelSettings


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config(
        api=ApiSettings(
            base_url="https://test.api.com",
            api_key="test-key",
            timeout=30,
            max_retries=3
        ),
        models=ModelSettings(
            supported_models=["model1", "model2", "model3"],
            default_models=["model1", "model2"],
            max_parallel_calls=2
        )
    )


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    client = AsyncMock()
    client.authenticate.return_value = True
    return client


@pytest.fixture
def model_service(mock_api_client, mock_config):
    """Create ModelService instance for testing."""
    return ModelService(mock_api_client, mock_config)


class TestModelServiceInitialization:
    """Test ModelService initialization."""
    
    def test_init_with_valid_config(self, mock_api_client, mock_config):
        """Test initialization with valid configuration."""
        service = ModelService(mock_api_client, mock_config)
        
        assert service.api_client == mock_api_client
        assert service.config == mock_config
        assert service.max_parallel_calls == 2
        assert service.model_settings == mock_config.models
    
    def test_init_sets_correct_attributes(self, mock_api_client, mock_config):
        """Test that initialization sets all required attributes."""
        service = ModelService(mock_api_client, mock_config)
        
        assert hasattr(service, 'api_client')
        assert hasattr(service, 'config')
        assert hasattr(service, 'model_settings')
        assert hasattr(service, 'max_parallel_calls')
        assert hasattr(service, 'logger')


class TestModelServiceMethods:
    """Test ModelService public methods."""
    
    def test_get_supported_models(self, model_service):
        """Test getting supported models list."""
        supported = model_service.get_supported_models()
        
        assert supported == ["model1", "model2", "model3"]
        assert isinstance(supported, list)
    
    def test_get_default_models(self, model_service):
        """Test getting default models list."""
        default = model_service.get_default_models()
        
        assert default == ["model1", "model2"]
        assert isinstance(default, list)
    
    def test_get_models_returns_copies(self, model_service):
        """Test that get methods return copies, not references."""
        supported1 = model_service.get_supported_models()
        supported2 = model_service.get_supported_models()
        
        # Modify one list
        supported1.append("new_model")
        
        # Other list should be unchanged
        assert "new_model" not in supported2
        assert len(supported2) == 3


@pytest.mark.asyncio
class TestCallModel:
    """Test single model call functionality."""
    
    async def test_call_model_success(self, model_service, mock_api_client):
        """Test successful model call."""
        # Setup mock response
        expected_response = ModelResponse(
            model_id="model1",
            content="Test response",
            duration=1.5,
            status=ResponseStatus.SUCCESS
        )
        mock_api_client.call_model.return_value = expected_response
        
        # Call the method
        result = await model_service.call_model("model1", "Test prompt")
        
        # Verify results
        assert result == expected_response
        mock_api_client.call_model.assert_called_once_with("model1", "Test prompt")
    
    async def test_call_model_with_kwargs(self, model_service, mock_api_client):
        """Test model call with additional parameters."""
        expected_response = ModelResponse(
            model_id="model1",
            content="Test response",
            duration=1.5,
            status=ResponseStatus.SUCCESS
        )
        mock_api_client.call_model.return_value = expected_response
        
        # Call with additional parameters
        result = await model_service.call_model(
            "model1", 
            "Test prompt", 
            temperature=0.7,
            max_tokens=100
        )
        
        # Verify parameters were passed through
        mock_api_client.call_model.assert_called_once_with(
            "model1", 
            "Test prompt", 
            temperature=0.7,
            max_tokens=100
        )
    
    async def test_call_model_empty_model_id(self, model_service):
        """Test call_model with empty model ID."""
        with pytest.raises(ValueError, match="Model ID cannot be empty"):
            await model_service.call_model("", "Test prompt")
        
        with pytest.raises(ValueError, match="Model ID cannot be empty"):
            await model_service.call_model("   ", "Test prompt")
    
    async def test_call_model_empty_prompt(self, model_service):
        """Test call_model with empty prompt."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            await model_service.call_model("model1", "")
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            await model_service.call_model("model1", "   ")
    
    async def test_call_model_api_exception(self, model_service, mock_api_client):
        """Test call_model when API client raises exception."""
        # Setup mock to raise exception
        mock_api_client.call_model.side_effect = Exception("API Error")
        
        # Call the method
        result = await model_service.call_model("model1", "Test prompt")
        
        # Verify error response
        assert result.model_id == "model1"
        assert result.status == ResponseStatus.ERROR
        assert "Unexpected error: API Error" in result.error_message
        assert result.content == ""
        assert result.duration == 0.0


@pytest.mark.asyncio
class TestCompareModels:
    """Test multi-model comparison functionality."""
    
    async def test_compare_models_success(self, model_service, mock_api_client):
        """Test successful comparison with multiple models."""
        # Setup mock responses
        response1 = ModelResponse(
            model_id="model1",
            content="Response 1",
            duration=1.0,
            status=ResponseStatus.SUCCESS
        )
        response2 = ModelResponse(
            model_id="model2", 
            content="Response 2",
            duration=1.5,
            status=ResponseStatus.SUCCESS
        )
        
        # Mock the call_model method to return different responses
        async def mock_call_model(model_id, prompt, **kwargs):
            if model_id == "model1":
                return response1
            elif model_id == "model2":
                return response2
            else:
                raise ValueError(f"Unexpected model_id: {model_id}")
        
        mock_api_client.call_model.side_effect = mock_call_model
        
        # Call compare_models
        result = await model_service.compare_models("Test prompt")
        
        # Verify results
        assert isinstance(result, ComparisonResult)
        assert result.prompt == "Test prompt"
        assert len(result.responses) == 2
        assert result.success_count == 2
        assert result.error_count == 0
        assert "model1" in result.responses
        assert "model2" in result.responses
        assert result.responses["model1"] == response1
        assert result.responses["model2"] == response2
    
    async def test_compare_models_with_custom_models(self, model_service, mock_api_client):
        """Test comparison with custom model list."""
        # Setup mock response
        response = ModelResponse(
            model_id="model3",
            content="Response 3",
            duration=1.0,
            status=ResponseStatus.SUCCESS
        )
        mock_api_client.call_model.return_value = response
        
        # Call with custom model list
        result = await model_service.compare_models("Test prompt", ["model3"])
        
        # Verify results
        assert len(result.responses) == 1
        assert "model3" in result.responses
        assert result.success_count == 1
    
    async def test_compare_models_empty_prompt(self, model_service):
        """Test compare_models with empty prompt."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            await model_service.compare_models("")
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            await model_service.compare_models("   ")
    
    async def test_compare_models_no_models(self, model_service):
        """Test compare_models with empty model list."""
        with pytest.raises(ValueError, match="No models specified for comparison"):
            await model_service.compare_models("Test prompt", [])
    
    async def test_compare_models_removes_duplicates(self, model_service, mock_api_client):
        """Test that duplicate model IDs are removed."""
        # Setup mock response
        response = ModelResponse(
            model_id="model1",
            content="Response",
            duration=1.0,
            status=ResponseStatus.SUCCESS
        )
        mock_api_client.call_model.return_value = response
        
        # Call with duplicate models
        result = await model_service.compare_models(
            "Test prompt", 
            ["model1", "model1", "model1"]
        )
        
        # Verify only one call was made
        assert len(result.responses) == 1
        assert mock_api_client.call_model.call_count == 1
    
    async def test_compare_models_partial_failure(self, model_service, mock_api_client):
        """Test comparison with some models failing."""
        # Setup mixed responses
        success_response = ModelResponse(
            model_id="model1",
            content="Success",
            duration=1.0,
            status=ResponseStatus.SUCCESS
        )
        error_response = ModelResponse(
            model_id="model2",
            content="",
            duration=0.5,
            status=ResponseStatus.ERROR,
            error_message="Model failed"
        )
        
        async def mock_call_model(model_id, prompt, **kwargs):
            if model_id == "model1":
                return success_response
            elif model_id == "model2":
                return error_response
            else:
                raise ValueError(f"Unexpected model_id: {model_id}")
        
        mock_api_client.call_model.side_effect = mock_call_model
        
        # Call compare_models
        result = await model_service.compare_models("Test prompt")
        
        # Verify mixed results
        assert result.success_count == 1
        assert result.error_count == 1
        assert result.total_models == 2
        assert result.responses["model1"].is_success
        assert result.responses["model2"].is_error


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check functionality."""
    
    async def test_health_check_all_healthy(self, model_service, mock_api_client):
        """Test health check when everything is working."""
        # Setup mocks
        mock_api_client.authenticate.return_value = True
        
        success_response = ModelResponse(
            model_id="test",
            content="Hello response",
            duration=0.5,
            status=ResponseStatus.SUCCESS
        )
        mock_api_client.call_model.return_value = success_response
        
        # Run health check
        health = await model_service.health_check()
        
        # Verify results
        assert health['api_authentication'] is True
        assert health['model_model1'] is True
        assert health['model_model2'] is True
        assert health['overall_health'] is True
    
    async def test_health_check_auth_failure(self, model_service, mock_api_client):
        """Test health check when authentication fails."""
        # Setup auth failure
        mock_api_client.authenticate.return_value = False
        
        # Run health check
        health = await model_service.health_check()
        
        # Verify results
        assert health['api_authentication'] is False
        assert 'overall_health' not in health  # Should not test models if auth fails
    
    async def test_health_check_model_failure(self, model_service, mock_api_client):
        """Test health check when some models fail."""
        # Setup mocks
        mock_api_client.authenticate.return_value = True
        
        async def mock_call_model(model_id, prompt, **kwargs):
            if model_id == "model1":
                return ModelResponse(
                    model_id=model_id,
                    content="Success",
                    duration=0.5,
                    status=ResponseStatus.SUCCESS
                )
            else:
                return ModelResponse(
                    model_id=model_id,
                    content="",
                    duration=0.5,
                    status=ResponseStatus.ERROR,
                    error_message="Model failed"
                )
        
        mock_api_client.call_model.side_effect = mock_call_model
        
        # Run health check
        health = await model_service.health_check()
        
        # Verify results
        assert health['api_authentication'] is True
        assert health['model_model1'] is True
        assert health['model_model2'] is False
        assert health['overall_health'] is False


@pytest.mark.asyncio
class TestParallelExecution:
    """Test parallel execution functionality."""
    
    async def test_parallel_execution_respects_concurrency_limit(self, model_service, mock_api_client):
        """Test that parallel execution respects max_parallel_calls limit."""
        # Track concurrent calls
        concurrent_calls = 0
        max_concurrent = 0
        
        async def mock_call_model(model_id, prompt, **kwargs):
            nonlocal concurrent_calls, max_concurrent
            concurrent_calls += 1
            max_concurrent = max(max_concurrent, concurrent_calls)
            
            # Simulate some work
            await asyncio.sleep(0.1)
            
            concurrent_calls -= 1
            return ModelResponse(
                model_id=model_id,
                content=f"Response from {model_id}",
                duration=0.1,
                status=ResponseStatus.SUCCESS
            )
        
        mock_api_client.call_model.side_effect = mock_call_model
        
        # Call with more models than the concurrency limit
        result = await model_service.compare_models(
            "Test prompt", 
            ["model1", "model2", "model3", "model4"]
        )
        
        # Verify concurrency was limited (max_parallel_calls = 2)
        assert max_concurrent <= 2
        assert len(result.responses) == 4
        assert result.success_count == 4


@pytest.mark.asyncio
class TestCleanup:
    """Test cleanup functionality."""
    
    async def test_close_calls_api_client_close(self, model_service, mock_api_client):
        """Test that close method calls API client close."""
        await model_service.close()
        
        mock_api_client.close.assert_called_once()
    
    async def test_close_handles_none_client(self, mock_config):
        """Test close method when API client is None."""
        service = ModelService(None, mock_config)
        
        # Should not raise exception
        await service.close()