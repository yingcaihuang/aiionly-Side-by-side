"""MAAS API client for model comparison system."""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

import httpx
from pydantic import ValidationError

from .models import (
    ApiResponse,
    ErrorInfo,
    ErrorType,
    ModelResponse,
    ResponseStatus,
)


logger = logging.getLogger(__name__)


class MaasApiClient:
    """HTTP client for interacting with the MAAS API."""
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """Initialize the MAAS API client.
        
        Args:
            base_url: Base URL for the MAAS API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Create HTTP client with default headers
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ModelComparisonSystem/1.0"
            }
        )
        
        logger.info(f"Initialized MAAS API client for {base_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.debug("MAAS API client closed")
    
    async def authenticate(self) -> bool:
        """Test authentication with the MAAS API.
        
        Returns:
            True if authentication is successful, False otherwise
        """
        try:
            # Try a simple API call to test authentication
            response = await self._make_request("GET", "/health")
            return response.success and not response.is_authentication_error
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            return False
    
    async def call_model(
        self,
        model_id: str,
        prompt: str,
        **kwargs
    ) -> ModelResponse:
        """Call a specific model with the given prompt.
        
        Args:
            model_id: ID of the model to call
            prompt: Text prompt to send to the model
            **kwargs: Additional parameters for the model call
            
        Returns:
            ModelResponse containing the result or error information
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not model_id or not model_id.strip():
                return self._create_error_response(
                    model_id,
                    "Model ID cannot be empty",
                    ErrorType.VALIDATION_ERROR,
                    start_time
                )
            
            if not prompt or not prompt.strip():
                return self._create_error_response(
                    model_id,
                    "Prompt cannot be empty",
                    ErrorType.VALIDATION_ERROR,
                    start_time
                )
            
            # Prepare request payload (OpenAI-compatible format)
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt.strip()
                    }
                ],
                **kwargs
            }
            
            # Make API call with retry logic
            response = await self._call_with_retry(
                "POST",
                "/v1/chat/completions",
                json=payload
            )
            
            # Process response
            if response.success and response.data:
                content = self._extract_content_from_response(response.data)
                return ModelResponse(
                    model_id=model_id,
                    content=content,
                    duration=time.time() - start_time,
                    status=ResponseStatus.SUCCESS
                )
            else:
                error_type = self._determine_error_type(response)
                # Parse and format error message in a user-friendly way
                friendly_error = self._format_error_message(response.error, response.status_code, response.data)
                return self._create_error_response(
                    model_id,
                    friendly_error,
                    error_type,
                    start_time
                )
                
        except asyncio.TimeoutError:
            return self._create_error_response(
                model_id,
                f"Request timed out after {self.timeout} seconds",
                ErrorType.TIMEOUT_ERROR,
                start_time
            )
        except Exception as e:
            logger.exception(f"Unexpected error calling model {model_id}")
            return self._create_error_response(
                model_id,
                f"Unexpected error: {str(e)}",
                ErrorType.UNKNOWN_ERROR,
                start_time
            )
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> ApiResponse:
        """Make an HTTP request to the MAAS API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for the request
            
        Returns:
            ApiResponse containing the result
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            response = await self.client.request(method, url, **kwargs)
            
            # Parse response
            try:
                data = response.json() if response.content else None
            except Exception:
                data = None
            
            return ApiResponse(
                success=response.is_success,
                data=data,
                error=None if response.is_success else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.TimeoutException:
            raise asyncio.TimeoutError("Request timed out")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            return ApiResponse(
                success=False,
                error=f"Network error: {str(e)}",
                status_code=0
            )
    
    async def _call_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> ApiResponse:
        """Make an API call with retry logic for rate limits and transient errors.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Request arguments
            
        Returns:
            ApiResponse from the successful call or final failure
        """
        last_response = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._make_request(method, endpoint, **kwargs)
                
                # If successful, return immediately
                if response.success:
                    return response
                
                # Handle rate limiting with exponential backoff
                if response.is_rate_limited and attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt, response)
                    logger.warning(
                        f"Rate limited, retrying in {delay} seconds "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                # Handle other retryable errors
                if self._is_retryable_error(response) and attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt, response)
                    logger.warning(
                        f"Retryable error (status {response.status_code}), "
                        f"retrying in {delay} seconds "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                # Non-retryable error or max retries reached
                last_response = response
                break
                
            except asyncio.TimeoutError:
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"Timeout, retrying in {delay} seconds "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
        
        return last_response or ApiResponse(
            success=False,
            error="Max retries exceeded",
            status_code=0
        )
    
    def _calculate_retry_delay(
        self,
        attempt: int,
        response: Optional[ApiResponse] = None
    ) -> float:
        """Calculate delay for retry attempts using exponential backoff.
        
        Args:
            attempt: Current attempt number (0-based)
            response: API response (may contain retry-after header)
            
        Returns:
            Delay in seconds
        """
        # Check for Retry-After header
        if response and response.headers:
            retry_after = response.headers.get('retry-after')
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
        
        # Exponential backoff: 1, 2, 4, 8, ... seconds (with jitter)
        base_delay = 2 ** attempt
        jitter = 0.1 * base_delay  # 10% jitter
        return min(base_delay + jitter, 60)  # Cap at 60 seconds
    
    def _is_retryable_error(self, response: ApiResponse) -> bool:
        """Determine if an error is retryable.
        
        Args:
            response: API response to check
            
        Returns:
            True if the error should be retried
        """
        # Retry on rate limits
        if response.is_rate_limited:
            return True
        
        # Retry on server errors (5xx)
        if 500 <= response.status_code < 600:
            return True
        
        # Retry on specific client errors that might be transient
        retryable_client_errors = {502, 503, 504}
        if response.status_code in retryable_client_errors:
            return True
        
        return False
    
    def _determine_error_type(self, response: ApiResponse) -> ErrorType:
        """Determine the error type based on the API response.
        
        Args:
            response: API response
            
        Returns:
            Appropriate ErrorType
        """
        if response.is_authentication_error:
            return ErrorType.AUTHENTICATION_ERROR
        elif response.is_rate_limited:
            return ErrorType.RATE_LIMIT_ERROR
        elif response.status_code == 0:
            return ErrorType.NETWORK_ERROR
        elif 400 <= response.status_code < 500:
            return ErrorType.VALIDATION_ERROR
        elif 500 <= response.status_code < 600:
            return ErrorType.MODEL_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _format_error_message(self, error_text: Optional[str], status_code: int, data: Optional[Dict[str, Any]]) -> str:
        """Format error message in a user-friendly way.
        
        Args:
            error_text: Raw error text from response
            status_code: HTTP status code
            data: Response data (may contain structured error info)
            
        Returns:
            User-friendly error message
        """
        # Try to extract structured error from JSON response
        if data and isinstance(data, dict):
            # Check for common error fields
            if 'error' in data:
                error_info = data['error']
                if isinstance(error_info, dict):
                    # Extract message from error object
                    if 'message' in error_info:
                        return f"API Error: {error_info['message']}"
                    elif 'code' in error_info and 'msg' in error_info:
                        return f"Error {error_info['code']}: {error_info['msg']}"
                elif isinstance(error_info, str):
                    return f"API Error: {error_info}"
            
            # Check for 'message' field
            if 'message' in data:
                return f"API Error: {data['message']}"
            
            # Check for 'msg' field
            if 'msg' in data:
                return f"API Error: {data['msg']}"
            
            # Check for 'detail' field
            if 'detail' in data:
                return f"API Error: {data['detail']}"
        
        # Parse common HTTP error patterns
        if error_text:
            # Remove HTML tags if present
            import re
            clean_text = re.sub(r'<[^>]+>', '', error_text)
            
            # Check if it's a JSON string
            if clean_text.strip().startswith('{'):
                try:
                    import json
                    error_json = json.loads(clean_text)
                    return self._format_error_message(None, status_code, error_json)
                except:
                    pass
            
            # If it's short and clean, use it directly
            if len(clean_text) < 200 and not clean_text.startswith('<!'):
                return clean_text.strip()
        
        # Fallback to status code based messages
        status_messages = {
            400: "Bad Request - The request was invalid or malformed",
            401: "Authentication Failed - Please check your API key",
            403: "Access Denied - You don't have permission to access this model",
            404: "Model Not Found - The requested model doesn't exist",
            429: "Rate Limit Exceeded - Too many requests, please try again later",
            500: "Model Service Error - The model service encountered an internal error",
            502: "Bad Gateway - The model service is temporarily unavailable",
            503: "Service Unavailable - The model service is temporarily down",
            504: "Gateway Timeout - The model service took too long to respond"
        }
        
        if status_code in status_messages:
            return status_messages[status_code]
        elif 400 <= status_code < 500:
            return f"Client Error ({status_code}) - There was a problem with the request"
        elif 500 <= status_code < 600:
            return f"Server Error ({status_code}) - The model service is experiencing issues"
        else:
            return f"Unknown Error ({status_code}) - An unexpected error occurred"
    
    def _extract_content_from_response(self, data: Dict[str, Any]) -> str:
        """Extract content from the API response data.
        
        Args:
            data: Response data from the API
            
        Returns:
            Extracted content string
        """
        try:
            # Handle OpenAI-style response format (primary format)
            if 'choices' in data and data['choices']:
                choice = data['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    return choice['message']['content']
            
            # Handle MAAS API response format (fallback)
            # Response structure: {"output": [{"content": [{"text": "..."}]}]}
            if 'output' in data and data['output']:
                output = data['output'][0]
                if 'content' in output and output['content']:
                    content_item = output['content'][0]
                    if 'text' in content_item:
                        return content_item['text']
            
            # Handle direct content field
            if 'content' in data:
                return data['content']
            
            # Handle text field
            if 'text' in data:
                return data['text']
            
            # Fallback: convert entire response to string
            return str(data)
            
        except Exception as e:
            logger.warning(f"Failed to extract content from response: {e}")
            return str(data)
    
    def _create_error_response(
        self,
        model_id: str,
        message: str,
        error_type: ErrorType,
        start_time: float
    ) -> ModelResponse:
        """Create a ModelResponse for error cases.
        
        Args:
            model_id: ID of the model
            message: Error message
            error_type: Type of error
            start_time: When the request started
            
        Returns:
            ModelResponse with error information
        """
        error_info = ErrorInfo(
            error_type=error_type,
            message=message,
            model_id=model_id
        )
        
        return ModelResponse(
            model_id=model_id,
            content="",
            duration=time.time() - start_time,
            status=ResponseStatus.ERROR,
            error_message=message,
            error_info=error_info
        )