"""Logging configuration for the Model Comparison System."""

import logging
import logging.config
from pathlib import Path
from typing import Dict, Any


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Set up logging configuration based on the provided config.
    
    Args:
        config: Logging configuration dictionary
    """
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            },
        },
        'handlers': {
            'console': {
                'level': config.get('level', 'INFO'),
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
        },
        'loggers': {
            'model_comparison_system': {
                'handlers': ['console'],
                'level': config.get('level', 'INFO'),
                'propagate': False
            },
        }
    }
    
    # Add file handler if log file is specified
    log_file = config.get('file')
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging_config['handlers']['file'] = {
            'level': config.get('level', 'INFO'),
            'class': 'logging.FileHandler',
            'filename': str(log_path),
            'formatter': 'standard',
        }
        logging_config['loggers']['model_comparison_system']['handlers'].append('file')
    
    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f'model_comparison_system.{name}')