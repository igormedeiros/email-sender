import logging
import logging.config
import os

def setup_logging():
    """Configura o logging para a aplicação."""
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': 'DEBUG',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': False
            },
            'email_sender': {
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': False
            },
        }
    }
    
    logging.config.dictConfig(logging_config)