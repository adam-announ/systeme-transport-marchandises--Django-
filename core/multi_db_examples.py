"""
Exemples d'utilisation de Neo4j et MongoDB
"""
from django.http import JsonResponse
from core.neo4j_connection import neo4j_conn
from core.mongo_models import TrackingLog, ActivityLog, RouteAnalytics
from core.mongo_connection import connect_mongodb


# Initialiser MongoDB au démarrage
connect_mongodb()


def save_tracking_position(request):
    """Sauvegarder la position GPS dans MongoDB"""
    tracking = TrackingLog(
        commande_id=request.POST.get('commande_id'),
        transporteur_id=request.user.id,
        latitude=float(request.POST.get('latitude')),
        longitude=float(request.POST.get('longitude')),
        vitesse=float(request.POST.get('vitesse', 0)),
        cap=float(request.POST.get('cap', 0))
    )
    tracking.save()
    
    return JsonResponse({'status': 'success', 'id': str(tracking.id)})


def get_tracking_history(request, commande_id):
    """Récupérer l'historique de tracking depuis MongoDB"""
    logs = TrackingLog.objects(commande_id=commande_id).order_by('-timestamp').limit(100)
    return JsonResponse({
        'tracking': [log.to_dict() for log in logs]
    })


def create_route_in_neo4j(request):
    """Créer un graphe d'itinéraire dans Neo4j"""
    result = neo4j_conn.create_route_graph(
        commande_id=request.POST.get('commande_id'),
        depart=request.POST.get('depart'),
        arrivee=request.POST.get('arrivee'),
        distance=float(request.POST.get('distance')),
        duree=float(request.POST.get('duree'))
    )
    
    return JsonResponse({'status': 'success', 'result': result})


def find_optimal_route(request):
    """Trouver l'itinéraire optimal avec Neo4j"""
    depart = request.GET.get('depart')
    arrivee = request.GET.get('arrivee')
    
    routes = neo4j_conn.find_optimal_routes(depart, arrivee)
    
    return JsonResponse({
        'routes': routes,
        'count': len(routes)
    })


def log_activity(request):
    """Logger une activité dans MongoDB"""
    log = ActivityLog(
        user_id=request.user.id,
        user_role=request.user.role,
        action=request.POST.get('action'),
        description=request.POST.get('description'),
        ip_address=request.META.get('REMOTE_ADDR'),
        metadata={'user_agent': request.META.get('HTTP_USER_AGENT')}
    )
    log.save()
    
    return JsonResponse({'status': 'logged'})
