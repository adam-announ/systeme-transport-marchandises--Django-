"""
Configuration et connexion MongoDB
"""
from mongoengine import connect, disconnect
from django.conf import settings


def connect_mongodb():
    """Établir la connexion MongoDB"""
    config = settings.MONGODB_CONFIG
    
    if config['USERNAME'] and config['PASSWORD']:
        connect(
            db=config['DB'],
            host=config['HOST'],
            port=config['PORT'],
            username=config['USERNAME'],
            password=config['PASSWORD'],
            authentication_source='admin'
        )
    else:
        connect(
            db=config['DB'],
            host=config['HOST'],
            port=config['PORT']
        )


def disconnect_mongodb():
    """Fermer la connexion MongoDB"""
    disconnect()
