"""
Application controller for the Model Comparison System.

This module orchestrates the comparison workflow and manages UI state.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

from model_comparison_system.config.config_service import ConfigService
from model_comparison_system.services.model_service import ModelService
from model_comparison_system.api.models import ModelResponse
from model_comparison_system.config.models import Config
from model_comparison_system.config.logging_config import get_logger


class AppController:
    """
    Application controller that orchestrates the model comparison workflow.
    
    This class manages the interaction between the UI and the backend services,
    handling prompt submission, validation, and state management.
    """
    
    def __init__(self, config_service: ConfigService, model_service: ModelService):
        """
        Initialize the application controller.
        
        Args:
            config_service: Service for configuration management
            model_service: Service for model API interactions
        """
        self.config_service = config_service
        self.model_service = model_service
        self.logger = get_logger('app_controller')
        self._current_config: Optional[Config] = None
        
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validate the current configuration.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            config = self.config_service.load_config()
            errors = self.config_service.validate_config(config)
            
            if not errors:
                self._current_config = config
                self.logger.info("Configuration validated successfully")
                return True, []
            else:
                self.logger.error(f"Configuration validation failed: {errors}")
                return False, errors
                
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            self.logger.error(error_msg)
            return False, [error_msg]
    
    def validate_prompt(self, prompt: str) -> Tuple[bool, str]:
            """
            Validate user prompt input with comprehensive checks.

            Args:
                prompt: The user's input prompt

            Returns:
                Tuple of (is_valid, error_message)
            """
            # Check for None or empty prompt
            if not prompt:
                return False, "Prompt cannot be empty. Please enter a valid prompt to compare models."

            # Check for whitespace-only prompt
            if not prompt.strip():
                return False, "Prompt cannot be empty or contain only whitespace. Please enter a meaningful prompt."

            # Check minimum length (at least 3 characters after stripping)
            stripped_prompt = prompt.strip()
            if len(stripped_prompt) < 3:
                return False, "Prompt is too short. Please enter at least 3 characters for a meaningful comparison."

            # Check maximum length
            if len(stripped_prompt) > 10000:
                return False, f"Prompt is too long ({len(stripped_prompt)} characters). Please limit to 10,000 characters or less."

            # Check for potentially problematic characters or patterns
            if '\x00' in prompt:
                return False, "Prompt contains invalid null characters. Please remove them and try again."

            # Check for excessive repetition (same character repeated more than 100 times)
            import re
            if re.search(r'(.)\1{99,}', prompt):
                return False, "Prompt contains excessive character repetition. Please provide a more varied prompt."

            # Check for reasonable line count (prevent extremely tall prompts)
            line_count = len(prompt.split('\n'))
            if line_count > 200:
                return False, f"Prompt has too many lines ({line_count}). Please limit to 200 lines or less."

            # All validations passed
            return True, ""

    
    async def submit_prompt(self, prompt: str, callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Submit a prompt for comparison across all configured models.
        
        Args:
            prompt: The user's input prompt
            callback: Optional callback function for streaming updates
                     Signature: callback(model_id: str, response: ModelResponse)
            
        Returns:
            Dictionary containing comparison results and metadata
        """
        self.logger.info(f"Submitting prompt for comparison: {prompt[:100]}...")
        
        # Validate prompt
        is_valid, error_msg = self.validate_prompt(prompt)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg,
                'responses': {},
                'metadata': {}
            }
        
        # Ensure configuration is loaded
        if not self._current_config:
            config_valid, config_errors = self.validate_configuration()
            if not config_valid:
                return {
                    'success': False,
                    'error': f"Configuration error: {'; '.join(config_errors)}",
                    'responses': {},
                    'metadata': {}
                }
        
        try:
            # Get model IDs from configuration
            model_ids = self._current_config.models.supported_models
            
            # Submit to model service for parallel processing with streaming callback
            start_time = datetime.now()
            comparison_result = await self.model_service.compare_models(prompt, model_ids, callback)
            end_time = datetime.now()
            
            self.logger.info(
                f"Comparison completed: {comparison_result.success_count} successful, "
                f"{comparison_result.error_count} failed, {comparison_result.total_duration:.2f}s total"
            )
            
            return {
                'success': True,
                'error': None,
                'responses': comparison_result.responses,
                'metadata': {
                    'prompt': comparison_result.prompt,
                    'total_duration': comparison_result.total_duration,
                    'success_count': comparison_result.success_count,
                    'error_count': comparison_result.error_count,
                    'timestamp': start_time.isoformat(),
                    'model_count': len(model_ids)
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to process comparison: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'responses': {},
                'metadata': {}
            }
    
    def get_model_status(self) -> Dict[str, str]:
        """
        Get the current status of all configured models.
        
        Returns:
            Dictionary mapping model IDs to their status
        """
        if not self._current_config:
            return {}
        
        model_ids = self._current_config.models.supported_models
        # For now, return all as available - could be enhanced to check actual availability
        return {model_id: "available" for model_id in model_ids}
    
    def get_supported_models(self) -> List[str]:
        """
        Get the list of supported model IDs.
        
        Returns:
            List of supported model IDs
        """
        return self.model_service.get_supported_models()
    
    def get_configuration_info(self) -> Dict[str, Any]:
        """
        Get current configuration information for display.
        
        Returns:
            Dictionary with configuration details
        """
        if not self._current_config:
            return {'loaded': False}
        
        return {
            'loaded': True,
            'api_base_url': self._current_config.api.base_url,
            'supported_models': self._current_config.models.supported_models,
            'max_parallel_calls': self._current_config.models.max_parallel_calls,
            'timeout': self._current_config.api.timeout
        }