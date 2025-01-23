import os
import logging
from logging import FileHandler

class Config:
    #Configuración base para todos los entornos.
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración de logging
    LOGGING_LEVEL = logging.INFO
    LOGGING_FILE = 'app.log'

    @classmethod
    def setup_logging(cls):
        #Configura el logger según el nivel y archivo especificado.
        handler = FileHandler(cls.LOGGING_FILE)
        handler.setLevel(cls.LOGGING_LEVEL)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

        app_logger = logging.getLogger()
        app_logger.setLevel(cls.LOGGING_LEVEL)
        app_logger.addHandler(handler)


class DevelopmentConfig(Config):
    """Configuración para entornos de desarrollo."""
    DEBUG = True
    FLASK_ENV = 'development'
    LOGGING_LEVEL = logging.DEBUG
    LOGGING_FILE = 'dev.log'
    SQLALCHEMY_DATABASE_URI = 'postgresql://dev_user:paradas_dev_2025@localhost/paradas_dev_db'



class ProductionConfig(Config):
    """Configuración para entornos de producción."""
    DEBUG = False
    FLASK_ENV = 'production'
    LOGGING_LEVEL = logging.WARNING
    LOGGING_FILE = 'prod.log'
    SQLALCHEMY_DATABASE_URI = 'postgresql://prod_user:paradas_prod_2025@localhost/paradas_prod_db'



# Carga de configuración y logging
def configure_app(app, config_class):
    """Aplica la configuración y configura el logging."""
    app.config.from_object(config_class)
    config_class.setup_logging()
