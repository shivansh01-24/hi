"""
Configuration settings for the application
"""
import os
import logging
from logging.handlers import RotatingFileHandler

# Application settings
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', 5000))

# API Keys and external services
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
IBM_QUANTUM_TOKEN = os.environ.get('IBM_QUANTUM_TOKEN')

# Optimization settings
DEFAULT_OPTIMIZATION_PARAMS = {
    'max_iterations': 1000,
    'convergence_threshold': 0.001,
    'population_size': 50
}

# OpenAI settings
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 1000
OPENAI_TEMPERATURE = 0.7

# Logging configuration
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'app.log'
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

def setup_logging():
    """Configure application-wide logging"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_SIZE,
                backupCount=LOG_BACKUP_COUNT
            ),
            logging.StreamHandler()
        ]
    )