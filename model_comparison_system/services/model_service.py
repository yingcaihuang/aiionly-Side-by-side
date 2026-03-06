"""Model service for orchestrating parallel API calls and managing model responses."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, TYPE_CHECKING

from ..api.maas_client import MaasApiClient
from ..api.models import ComparisonResult, ModelResponse, ResponseStatus
from ..config.models import Config

if TYPE_CHECKING:
    from ..services.error_service import ErrorHandler


logger = logging.getLogger(__name__)


class ModelService:
    """Service for managing parallel model API calls and response processing."""
    
    def __init__(self, api_client: MaasApiClient, config: Config, error_handler: Optional['ErrorHandler'] = None):
        """Initialize ModelService with API client and configuration.
        
        Args:
            api_client: MAAS API client for making model calls
            config: Application configuration
            error_handler: Error handler for centralized error management (optional)
        """
        self.api_client = api_client
        self.config = config
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        
        # Get model settings for convenience
        self.model_settings = config.models
        self.max_parallel_calls = self.model_settings.max_parallel_calls
        
        logger.info(f"ModelService initialized with {len(self.model_settings.default_models)} default models")
    
    async def compare_models(
        self,
        prompt: str,
        model_ids: Optional[List[str]] = None,
        callback: Optional[callable] = None
    ) -> ComparisonResult:
        """Compare responses from multiple models using the same prompt.
        
        Args:
            prompt: Text prompt to send to all models
            model_ids: List of model IDs to use (defaults to configured default models)
            callback: Optional callback function called when each model completes
                     Signature: callback(model_id: str, response: ModelResponse)
            
        Returns:
            ComparisonResult containing responses from all models
        """
        start_time = time.time()
        
        # Use default models if none specified
        if model_ids is None:
            model_ids = self.model_settings.default_models.copy()
        
        # Validate inputs
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        if not model_ids:
            raise ValueError("No models specified for comparison")
        
        # Remove duplicates while preserving order
        unique_model_ids = []
        seen = set()
        for model_id in model_ids:
            if model_id not in seen:
                unique_model_ids.append(model_id)
                seen.add(model_id)
        
        model_ids = unique_model_ids
        
        logger.info(f"Starting comparison with {len(model_ids)} models: {model_ids}")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
        # Execute parallel model calls with streaming callback
        responses = await self._execute_parallel_calls(prompt, model_ids, callback)
        
        # Calculate statistics
        success_count = sum(1 for response in responses.values() if response.is_success)
        error_count = len(responses) - success_count
        total_duration = time.time() - start_time
        
        result = ComparisonResult(
            prompt=prompt,
            responses=responses,
            total_duration=total_duration,
            success_count=success_count,
            error_count=error_count
        )
        
        logger.info(
            f"Comparison completed: {success_count}/{len(model_ids)} successful, "
            f"total time: {total_duration:.2f}s"
        )
        
        return result
    
    async def call_model(
        self,
        model_id: str,
        prompt: str,
        **kwargs
    ) -> ModelResponse:
        """Call a single model with the given prompt.
        
        Args:
            model_id: ID of the model to call
            prompt: Text prompt to send to the model
            **kwargs: Additional parameters for the model call
            
        Returns:
            ModelResponse containing the result or error information
        """
        # Validate inputs
        if not model_id or not model_id.strip():
            raise ValueError("Model ID cannot be empty")
        
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        # Check if model is supported
        if model_id not in self.model_settings.supported_models:
            logger.warning(f"Model {model_id} is not in supported models list")
        
        logger.debug(f"Calling model {model_id} with prompt length: {len(prompt)}")
        
        try:
            response = await self.api_client.call_model(model_id, prompt, **kwargs)
            
            # Log the API interaction
            if self.error_handler:
                self.error_handler.log_api_interaction(
                    model_id=model_id,
                    prompt=prompt,
                    response=response,
                    duration=response.duration
                )
            
            if response.is_success:
                logger.debug(f"Model {model_id} responded successfully in {response.duration:.2f}s")
            else:
                logger.warning(f"Model {model_id} failed: {response.error_message}")
            
            return response
            
        except Exception as e:
            logger.exception(f"Unexpected error calling model {model_id}")
            
            # Use error handler if available
            if self.error_handler:
                self.error_handler.log_api_interaction(
                    model_id=model_id,
                    prompt=prompt,
                    error=e
                )
                # Let the error handler create the response
                return await self.error_handler.handle_model_error(e, model_id)
            else:
                # Fallback error response creation
                return ModelResponse(
                    model_id=model_id,
                    content="",
                    duration=0.0,
                    status=ResponseStatus.ERROR,
                    error_message=f"Unexpected error: {str(e)}"
                )
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported model IDs.
        
        Returns:
            List of supported model IDs
        """
        return self.model_settings.supported_models.copy()
    
    def get_default_models(self) -> List[str]:
        """Get list of default model IDs.
        
        Returns:
            List of default model IDs
        """
        return self.model_settings.default_models.copy()
    
    async def _execute_parallel_calls(
        self,
        prompt: str,
        model_ids: List[str],
        callback: Optional[callable] = None
    ) -> Dict[str, ModelResponse]:
        """Execute parallel API calls to multiple models.
        
        Args:
            prompt: Text prompt to send to all models
            model_ids: List of model IDs to call
            callback: Optional callback function called when each model completes
            
        Returns:
            Dictionary mapping model IDs to their responses
        """
        # Create semaphore to limit concurrent calls
        semaphore = asyncio.Semaphore(self.max_parallel_calls)
        
        async def call_with_semaphore(model_id: str) -> tuple[str, ModelResponse]:
            """Call a model with semaphore protection."""
            async with semaphore:
                response = await self.call_model(model_id, prompt)
                # Call the callback if provided
                if callback:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(model_id, response)
                        else:
                            callback(model_id, response)
                    except Exception as e:
                        logger.error(f"Error in callback for model {model_id}: {e}")
                return model_id, response
        
        # Create tasks for all model calls
        tasks = [
            call_with_semaphore(model_id)
            for model_id in model_ids
        ]
        
        logger.debug(f"Created {len(tasks)} parallel tasks with max concurrency: {self.max_parallel_calls}")
        
        # Execute all tasks and collect results
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.exception("Error in parallel model execution")
            # Create error responses for all models
            return {
                model_id: ModelResponse(
                    model_id=model_id,
                    content="",
                    duration=0.0,
                    status=ResponseStatus.ERROR,
                    error_message=f"Parallel execution failed: {str(e)}"
                )
                for model_id in model_ids
            }
        
        # Process results and handle exceptions
        responses = {}
        for i, result in enumerate(results):
            model_id = model_ids[i]
            
            if isinstance(result, Exception):
                # Handle task-level exceptions
                logger.error(f"Task for model {model_id} raised exception: {result}")
                responses[model_id] = ModelResponse(
                    model_id=model_id,
                    content="",
                    duration=0.0,
                    status=ResponseStatus.ERROR,
                    error_message=f"Task execution failed: {str(result)}"
                )
            else:
                # Normal result (model_id, response tuple)
                result_model_id, response = result
                responses[result_model_id] = response
        
        return responses
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on the API client and models.
        
        Returns:
            Dictionary with health status for API client and models
        """
        health_status = {}
        
        # Check API client authentication
        try:
            auth_success = await self.api_client.authenticate()
            health_status['api_authentication'] = auth_success
            
            if not auth_success:
                logger.warning("API authentication failed during health check")
                # Don't test models if authentication fails
                return health_status
                
        except Exception as e:
            logger.exception("Error during API authentication health check")
            health_status['api_authentication'] = False
            return health_status
        
        # Test a simple call to each default model
        test_prompt = "Hello"
        model_health = {}
        
        for model_id in self.model_settings.default_models:
            try:
                response = await self.call_model(model_id, test_prompt)
                model_health[f'model_{model_id}'] = response.is_success
                
                if not response.is_success:
                    logger.warning(f"Model {model_id} health check failed: {response.error_message}")
                    
            except Exception as e:
                logger.exception(f"Error during health check for model {model_id}")
                model_health[f'model_{model_id}'] = False
        
        health_status.update(model_health)
        
        # Overall health summary
        all_healthy = all(health_status.values())
        health_status['overall_health'] = all_healthy
        
        logger.info(f"Health check completed: {sum(health_status.values())}/{len(health_status)} checks passed")
        
        return health_status
    
    async def close(self):
        """Close the model service and clean up resources."""
        if self.api_client:
            await self.api_client.close()
        logger.info("ModelService closed")