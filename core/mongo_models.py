"""
Modèles MongoDB pour le système de transport
"""
from mongoengine import Document, fields
from datetime import datetime


class TrackingLog(Document):
    """Logs de tracking en temps réel"""
    
    commande_id = fields.IntField(required=True)
    transporteur_id = fields.IntField(required=True)
    latitude = fields.FloatField(required=True)
    longitude = fields.FloatField(required=True)
    vitesse = fields.FloatField(default=0)
    cap = fields.FloatField(default=0)
    timestamp = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'tracking_logs',
        'indexes': [
            'commande_id',
            'transporteur_id',
            '-timestamp'
        ]
    }
    
    def to_dict(self):
        return {
            'commande_id': self.commande_id,
            'transporteur_id': self.transporteur_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'vitesse': self.vitesse,
            'cap': self.cap,
            'timestamp': self.timestamp.isoformat()
        }


class ActivityLog(Document):
    """Logs d'activité système"""
    
    user_id = fields.IntField(required=True)
    user_role = fields.StringField(required=True)
    action = fields.StringField(required=True)
    description = fields.StringField()
    ip_address = fields.StringField()
    metadata = fields.DictField()
    timestamp = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'activity_logs',
        'indexes': [
            'user_id',
            '-timestamp',
            'action'
        ]
    }
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'user_role': self.user_role,
            'action': self.action,
            'description': self.description,
            'ip_address': self.ip_address,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class RouteAnalytics(Document):
    """Analytics des itinéraires"""
    
    route_hash = fields.StringField(required=True, unique=True)
    depart = fields.StringField(required=True)
    arrivee = fields.StringField(required=True)
    distance_moyenne = fields.FloatField()
    duree_moyenne = fields.FloatField()
    nombre_trajets = fields.IntField(default=0)
    cout_moyen = fields.FloatField()
    conditions_meteo = fields.ListField(fields.DictField())
    last_updated = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'route_analytics',
        'indexes': ['route_hash', 'depart', 'arrivee']
    }
