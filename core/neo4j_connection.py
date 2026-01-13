"""
Connexion et modèles Neo4j pour le système de transport
"""
from neo4j import GraphDatabase
from django.conf import settings


class Neo4jConnection:
    """Gestionnaire de connexion Neo4j"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_CONFIG['URI'],
            auth=(
                settings.NEO4J_CONFIG['USERNAME'],
                settings.NEO4J_CONFIG['PASSWORD']
            )
        )
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def query(self, query, parameters=None):
        """Exécuter une requête Cypher"""
        with self.driver.session(database=settings.NEO4J_CONFIG['DATABASE']) as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]
    
    def create_route_graph(self, commande_id, depart, arrivee, distance, duree):
        """Créer un graphe d'itinéraire"""
        query = """
        MERGE (d:Location {name: $depart})
        MERGE (a:Location {name: $arrivee})
        CREATE (d)-[r:ROUTE {
            commande_id: $commande_id,
            distance: $distance,
            duree: $duree,
            created_at: datetime()
        }]->(a)
        RETURN r
        """
        return self.query(query, {
            'commande_id': commande_id,
            'depart': depart,
            'arrivee': arrivee,
            'distance': distance,
            'duree': duree
        })
    
    def find_optimal_routes(self, depart, arrivee):
        """Trouver les itinéraires optimaux"""
        query = """
        MATCH path = shortestPath(
            (d:Location {name: $depart})-[*]-(a:Location {name: $arrivee})
        )
        RETURN path, length(path) as hops
        ORDER BY hops
        LIMIT 5
        """
        return self.query(query, {'depart': depart, 'arrivee': arrivee})


# Instance globale
neo4j_conn = Neo4jConnection()
