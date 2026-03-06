"""Unit tests for MAAS API client."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from model_comparison_system.api.maas_client import MaasApiClient
from model_comparison_system.api.models import (
    ApiResponse,
    ErrorType,
    ModelResponse,
    ResponseStatus,
)


class TestMaasApiClient:
    """Test cases for MaasApiClient."""
    
    @pytest.fixture
    def client(self):
        """Create a test MAAS API client."""
        return MaasApiClient(
            base_url="https://test-api.example.com",
            api_key="test-api-key",
            timeout=10,
            max_retries=2
        )
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx.AsyncClient."""
        with patch('model_comparison_system.api.maas_client.httpx.AsyncClient') as mock:
            yield mock
    
    def test_client_initialization(self, client):
        """Test client initialization with proper parameters."""
        assert client.base_url == "https://test-api.example.com"
        assert client.api_key == "test-api-key"
        assert client.timeout == 10
        assert client.max_retries == 2
    
    def test_client_initialization_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        client = MaasApiClient(
            base_url="https://test-api.example.com/",
            api_key="test-key"
        )
        assert client.base_url == "https://test-api.example.com"
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_httpx_client):
        """Test async context manager functionality."""
        mock_client_instance = AsyncMock()
        mock_httpx_client.return_value = mock_client_instance
        
        async with MaasApiClient("https://test.com", "key") as client:
            assert client is not None
        
        mock_client_instance.aclose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client close functionality."""
        client.client = AsyncMock()
        await client.close()
        client.client.aclose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, client):
        """Test successful authentication."""
        # Mock successful health check response
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.content = b'{"status": "ok"}'
        mock_response.text = '{"status": "ok"}'
        mock_response.headers = {}
        
        client.client = AsyncMock()
        client.client.request.return_value = mock_response
        
        result = await client.authenticate()
        assert result is True
        client.client.request.assert_called_once_with("GET", "https://test-api.example.com/health")
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, client):
        """Test authentication failure."""
        # Mock authentication error response
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_response.content = b'{"error": "Unauthorized"}'
        mock_response.text = '{"error": "Unauthorized"}'
        mock_response.headers = {}
        
        client.client = AsyncMock()
        client.client.request.return_value = mock_response
        
        result = await client.authenticate()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_exception(self, client):
        """Test authentication with exception."""
        client.client = AsyncMock()
        client.client.request.side_effect = Exception("Network error")
        
        result = await client.authenticate()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_call_model_success(self, client):
        """Test successful model call."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is a test response from the model."
                    }
                }
            ]
        }
        mock_response.content = b'{"choices": [{"message": {"content": "This is a test response from the model."}}]}'
        mock_response.text = '{"choices": [{"message": {"content": "This is a test response from the model."}}]}'
        mock_response.headers = {}
        
        client.client = AsyncMock()
        client.client.request.return_value = mock_response
        
        result = await client.call_model("test-model", "Hello, world!")
        
        assert isinstance(result, ModelResponse)
        assert result.model_id == "test-model"
        assert result.content == "This is a test response from the model."
        assert result.status == ResponseStatus.SUCCESS
        assert result.duration > 0
        assert result.is_success is True
        assert result.is_error is False
    
    @pytest.mark.asyncio
    async def test_call_model_empty_model_id(self, client):
        """Test model call with empty model ID."""
        result = await client.call_model("", "Hello, world!")
        
        assert isinstance(result, ModelResponse)
        assert result.status == ResponseStatus.ERROR
        assert result.error_info.error_type == ErrorType.VALIDATION_ERROR
        assert "Model ID cannot be empty" in result.error_message
    
    @pytest.mark.asyncio
    async def test_call_model_empty_prompt(self, client):
        """Test model call with empty prompt."""
        result = await client.call_model("test-model", "")
        
        assert isinstance(result, ModelResponse)
        assert result.status == ResponseStatus.ERROR
        assert result.error_info.error_type == ErrorType.VALIDATION_ERROR
        assert "Prompt cannot be empty" in result.error_message
    
    @pytest.mark.asyncio
    async def test_call_model_api_error(self, client):
        """Test model call with API error."""
        # Mock API error response
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_response.content = b'{"error": "Bad request"}'
        mock_response.text = '{"error": "Bad request"}'
        mock_response.headers = {}
        
        client.client = AsyncMock()
        client.client.request.return_value = mock_response
        
        result = await client.call_model("test-model", "Hello, world!")
        
        assert isinstance(result, ModelResponse)
        assert result.status == ResponseStatus.ERROR
        assert result.error_info.error_type == ErrorType.VALIDATION_ERROR
        assert "Bad request" in result.error_message
    
    @pytest.mark.asyncio
    async def test_call_model_timeout(self, client):
        """Test model call with timeout."""
        client.client = AsyncMock()
        client.client.request.side_effect = httpx.TimeoutException("Request timed out")
        
        result = await client.call_model("test-model", "Hello, world!")
        
        assert isinstance(result, ModelResponse)
        assert result.status == ResponseStatus.ERROR
        assert result.error_info.error_type == ErrorType.TIMEOUT_ERROR
        assert "timed out" in result.error_message
    
    @pytest.mark.asyncio
    async def test_call_model_unexpected_error(self, client):
        """Test model call with unexpected error."""
        client.client = AsyncMock()
        client.client.request.side_effect = Exception("Unexpected error")
        
        result = await client.call_model("test-model", "Hello, world!")
        
        assert isinstance(result, ModelResponse)
        assert result.status == ResponseStatus.ERROR
        assert result.error_info.error_type == ErrorType.UNKNOWN_ERROR
        assert "Unexpected error" in result.error_message
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, client):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.content = b'{"data": "test"}'
        mock_response.text = '{"data": "test"}'
        mock_response.headers = {"Content-Type": "application/json"}
        
        client.client = AsyncMock()
        client.client.request.return_value = mock_response
        
        result = await client._make_request("GET", "/test")
        
        assert isinstance(result, ApiResponse)
        assert result.success is True
        assert result.data == {"data": "test"}
        assert result.status_code == 200
        assert result.headers["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_make_request_network_error(self, client):
        """Test HTTP request with network error."""
        client.client = AsyncMock()
        client.client.request.side_effect = httpx.RequestError("Network error")
        
        result = await client._make_request("GET", "/test")
        
        assert isinstance(result, ApiResponse)
        assert result.success is False
        assert "Network error" in result.error
        assert result.status_code == 0
    
    @pytest.mark.asyncio
    async def test_make_request_timeout(self, client):
        """Test HTTP request with timeout."""
        client.client = AsyncMock()
        client.client.request.side_effect = httpx.TimeoutException("Timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await client._make_request("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_call_with_retry_success_first_attempt(self, client):
        """Test retry logic with success on first attempt."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.content = b'{"data": "test"}'
        mock_response.text = '{"data": "test"}'
        mock_response.headers = {}
        
        client.client = AsyncMock()
        client.client.request.return_value = mock_response
        
        result = await client._call_with_retry("GET", "/test")
        
        assert result.success is True
        assert client.client.request.call_count == 1
    
    @pytest.mark.asyncio
    async def test_call_with_retry_rate_limit_then_success(self, client):
        """Test retry logic with rate limit then success."""
        # First call: rate limited
        rate_limit_response = Mock()
        rate_limit_response.is_success = False
        rate_limit_response.status_code = 429
        rate_limit_response.json.return_value = {"error": "Rate limited"}
        rate_limit_response.content = b'{"error": "Rate limited"}'
        rate_limit_response.text = '{"error": "Rate limited"}'
        rate_limit_response.headers = {"retry-after": "1"}
        
        # Second call: success
        success_response = Mock()
        success_response.is_success = True
        success_response.status_code = 200
        success_response.json.return_value = {"data": "test"}
        success_response.content = b'{"data": "test"}'
        success_response.text = '{"data": "test"}'
        success_response.headers = {}
        
        client.client = AsyncMock()
        client.client.request.side_effect = [rate_limit_response, success_response]
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await client._call_with_retry("GET", "/test")
        
        assert result.success is True
        assert client.client.request.call_count == 2
        mock_sleep.assert_called_once_with(1.0)  # retry-after header value
    
    @pytest.mark.asyncio
    async def test_call_with_retry_max_retries_exceeded(self, client):
        """Test retry logic when max retries are exceeded."""
        # All calls return rate limit error
        rate_limit_response = Mock()
        rate_limit_response.is_success = False
        rate_limit_response.status_code = 429
        rate_limit_response.json.return_value = {"error": "Rate limited"}
        rate_limit_response.content = b'{"error": "Rate limited"}'
        rate_limit_response.text = '{"error": "Rate limited"}'
        rate_limit_response.headers = {}
        
        client.client = AsyncMock()
        client.client.request.return_value = rate_limit_response
        
        with patch('asyncio.sleep'):
            result = await client._call_with_retry("GET", "/test")
        
        assert result.success is False
        assert result.status_code == 429
        # Should try initial + max_retries times
        assert client.client.request.call_count == client.max_retries + 1
    
    def test_calculate_retry_delay_with_retry_after_header(self, client):
        """Test retry delay calculation with Retry-After header."""
        response = ApiResponse(
            success=False,
            status_code=429,
            headers={"retry-after": "5"}
        )
        
        delay = client._calculate_retry_delay(0, response)
        assert delay == 5.0
    
    def test_calculate_retry_delay_exponential_backoff(self, client):
        """Test retry delay calculation with exponential backoff."""
        # First attempt (attempt=0): 2^0 = 1 second + jitter
        delay0 = client._calculate_retry_delay(0)
        assert 1.0 <= delay0 <= 1.2  # 1 + 10% jitter
        
        # Second attempt (attempt=1): 2^1 = 2 seconds + jitter
        delay1 = client._calculate_retry_delay(1)
        assert 2.0 <= delay1 <= 2.4  # 2 + 10% jitter
        
        # Third attempt (attempt=2): 2^2 = 4 seconds + jitter
        delay2 = client._calculate_retry_delay(2)
        assert 4.0 <= delay2 <= 4.8  # 4 + 10% jitter
    
    def test_calculate_retry_delay_max_cap(self, client):
        """Test retry delay calculation respects maximum cap."""
        # Large attempt number should be capped at 60 seconds
        delay = client._calculate_retry_delay(10)
        assert delay <= 60.0
    
    def test_is_retryable_error_rate_limit(self, client):
        """Test retryable error detection for rate limits."""
        response = ApiResponse(success=False, status_code=429)
        assert client._is_retryable_error(response) is True
    
    def test_is_retryable_error_server_errors(self, client):
        """Test retryable error detection for server errors."""
        for status_code in [500, 502, 503, 504]:
            response = ApiResponse(success=False, status_code=status_code)
            assert client._is_retryable_error(response) is True
    
    def test_is_retryable_error_non_retryable(self, client):
        """Test retryable error detection for non-retryable errors."""
        for status_code in [400, 401, 403, 404]:
            response = ApiResponse(success=False, status_code=status_code)
            assert client._is_retryable_error(response) is False
    
    def test_determine_error_type_authentication(self, client):
        """Test error type determination for authentication errors."""
        response = ApiResponse(success=False, status_code=401)
        error_type = client._determine_error_type(response)
        assert error_type == ErrorType.AUTHENTICATION_ERROR
    
    def test_determine_error_type_rate_limit(self, client):
        """Test error type determination for rate limit errors."""
        response = ApiResponse(success=False, status_code=429)
        error_type = client._determine_error_type(response)
        assert error_type == ErrorType.RATE_LIMIT_ERROR
    
    def test_determine_error_type_network(self, client):
        """Test error type determination for network errors."""
        response = ApiResponse(success=False, status_code=0)
        error_type = client._determine_error_type(response)
        assert error_type == ErrorType.NETWORK_ERROR
    
    def test_determine_error_type_validation(self, client):
        """Test error type determination for validation errors."""
        response = ApiResponse(success=False, status_code=400)
        error_type = client._determine_error_type(response)
        assert error_type == ErrorType.VALIDATION_ERROR
    
    def test_determine_error_type_model_error(self, client):
        """Test error type determination for model errors."""
        response = ApiResponse(success=False, status_code=500)
        error_type = client._determine_error_type(response)
        assert error_type == ErrorType.MODEL_ERROR
    
    def test_extract_content_from_response_openai_format(self, client):
        """Test content extraction from OpenAI-style response."""
        data = {
            "choices": [
                {
                    "message": {
                        "content": "Test response content"
                    }
                }
            ]
        }
        
        content = client._extract_content_from_response(data)
        assert content == "Test response content"
    
    def test_extract_content_from_response_direct_content(self, client):
        """Test content extraction from direct content field."""
        data = {"content": "Direct content"}
        content = client._extract_content_from_response(data)
        assert content == "Direct content"
    
    def test_extract_content_from_response_text_field(self, client):
        """Test content extraction from text field."""
        data = {"text": "Text field content"}
        content = client._extract_content_from_response(data)
        assert content == "Text field content"
    
    def test_extract_content_from_response_fallback(self, client):
        """Test content extraction fallback to string conversion."""
        data = {"unknown_format": "some data"}
        content = client._extract_content_from_response(data)
        assert "unknown_format" in content
        assert "some data" in content
    
    def test_create_error_response(self, client):
        """Test error response creation."""
        start_time = 1000.0
        
        with patch('time.time', return_value=1001.5):
            response = client._create_error_response(
                "test-model",
                "Test error message",
                ErrorType.NETWORK_ERROR,
                start_time
            )
        
        assert isinstance(response, ModelResponse)
        assert response.model_id == "test-model"
        assert response.error_message == "Test error message"
        assert response.status == ResponseStatus.ERROR
        assert response.error_info.error_type == ErrorType.NETWORK_ERROR
        assert response.duration == 1.5  # 1001.5 - 1000.0