"""
Configuration Module
====================
Centralized configuration management using environment variables.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'

    # MongoDB
    MONGO_URI = os.getenv(
        'MONGO_URI',
        'mongodb://localhost:27017/drowsiness_db'
    )
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'drowsiness_db')

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))
    )

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # Device Auth
    DEVICE_API_KEY = os.getenv('DEVICE_API_KEY', 'default-device-key')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    RATELIMIT_DEFAULT = "100 per hour"


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
