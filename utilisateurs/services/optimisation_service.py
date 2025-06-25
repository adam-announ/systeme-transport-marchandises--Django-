# utilisateurs/services/planification_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Count
from ..models import (
    Commande, Vehicule, User, Tournee, EtapeTournee, 
    Livraison, Notification
)
from .optimisation_service import OptimisationService
from .api_service import TransportAPIService

class PlanificationService:
    """Service pour la planification automatique et intelligente des tournées"""
    
    @staticmethod
    def planification_automatique_journaliere(date_cible: datetime = None, 
                                            planificateur_id: int = None) -> Dict:
        """
        Planifie automatiquement toutes les commandes en attente pour une journée donnée
        """
        if not date_cible:
            date_cible = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        # Récupérer les commandes en attente pour cette date
        commandes_disponibles = Commande.objects.filter(
            statut='en_attente',
            date_livraison_prevue__date=date_cible.date()
        ).order_by('priorite', 'date_creation')
        
        if not commandes_disponibles.exists():
            return {
                'success': False,
                'message': 'Aucune commande en attente pour cette date',
                'tournees_creees': 0
            }
        
        # Récupérer les véhicules disponibles
        vehicules_disponibles = Vehicule.objects.filter(
            disponible=True,
            transporteur__is_active=True
        ).select_related('transporteur')
        
        if not vehicules_disponibles.exists():
            return {
                'success': False,
                'message': 'Aucun véhicule disponible',
                'tournees_creees': 0
            }
        
        # Vérifier les conditions météo
        conditions_meteo = TransportAPIService.check_weather_conditions_for_transport("Casablanca")
        if not conditions_meteo.get('suitable', True):
            return {
                'success': False,
                'message': f"Conditions météo défavorables: {conditions_meteo.get('message', '')}",
                'tournees_creees': 0,
                'warnings': conditions_meteo.get('warnings', [])
            }
        
        # Grouper les commandes par zones géographiques
        zones_commandes = PlanificationService.grouper_par_zones(list(commandes_disponibles))
        
        tournees_creees = []
        commandes_traitees = []
        erreurs = []
        
        try:
            with transaction.atomic():
                for zone, commandes_zone in zones_commandes.items():
                    # Répartir les commandes de cette zone entre les véhicules disponibles
                    try:
                        tournees_zone = PlanificationService.repartir_commandes_vehicules(
                            commandes_zone, 
                            list(vehicules_disponibles),
                            date_cible,
                            planificateur_id
                        )
                        
                        tournees_creees.extend(tournees_zone)
                        commandes_traitees.extend([cmd for tournee in tournees_zone 
                                                 for cmd in tournee['commandes']])
                        
                        # Marquer les véhicules utilisés comme non disponibles temporairement
                        vehicules_utilises = [t['vehicule'].id for t in tournees_zone]
                        vehicules_disponibles = vehicules_disponibles.exclude(id__in=vehicules_utilises)
                        
                        if not vehicules_disponibles.exists():
                            break
                            
                    except Exception as e:
                        erreurs.append(f"Erreur zone {zone}: {str(e)}")
                        continue
                
                # Créer les tournées en base de données
                tournees_db = []
                for tournee_info in tournees_creees:
                    try:
                        tournee_db = PlanificationService.creer_tournee_db(
                            tournee_info, planificateur_id
                        )
                        tournees_db.append(tournee_db)
                    except Exception as e:
                        erreurs.append(f"Erreur création tournée: {str(e)}")
                
                commandes_restantes = commandes_disponibles.count() - len(commandes_traitees)
                
                result = {
                    'success': True,
                    'message': f'{len(tournees_creees)} tournée(s) créée(s) avec succès',
                    'tournees_creees': len(tournees_creees),
                    'commandes_traitees': len(commandes_traitees),
                    'commandes_restantes': commandes_restantes,
                    'tournees': tournees_db,
                    'conditions_meteo': conditions_meteo
                }
                
                if erreurs:
                    result['warnings'] = erreurs
                
                if commandes_restantes > 0:
                    result['message'] += f" ({commandes_restantes} commande(s) restante(s))"
                
                return result
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la planification: {str(e)}',
                'tournees_creees': 0,
                'erreurs': erreurs
            }
    
    @staticmethod
    def grouper_par_zones(commandes: List[Commande]) -> Dict[str, List[Commande]]:
        """Groupe les commandes par zones géographiques améliorées"""
        zones = {
            'casablanca_centre': [],
            'casablanca_peripherie': [],
            'rabat_sale': [],
            'marrakech': [],
            'fes_meknes': [],
            'tanger_tetouan': [],
            'agadir_region': [],
            'oujda_oriental': [],
            'autres': []
        }
        
        # Zones géographiques détaillées
        zones_mapping = {
            'casablanca_centre': ['casablanca centre', 'casa centre', 'ain diab', 'maarif', 'racine'],
            'casablanca_peripherie': ['casablanca', 'casa', 'mohammedia', 'benslimane', 'berrechid'],
            'rabat_sale': ['rabat', 'sale', 'salé', 'temara', 'skhirat', 'kenitra', 'kénitra'],
            'marrakech': ['marrakech', 'marrakesh', 'essaouira', 'safi'],
            'fes_meknes': ['fes', 'fez', 'fès', 'meknes', 'meknès', 'ifrane'],
            'tanger_tetouan': ['tanger', 'tangier', 'tetouan', 'tétouan', 'larache', 'chefchaouen'],
            'agadir_region': ['agadir', 'inezgane', 'tiznit', 'taroudant'],
            'oujda_oriental': ['oujda', 'nador', 'berkane', 'bouarfa']
        }
        
        for commande in commandes:
            zone_trouvee = False
            
            # Analyser l'origine et la destination
            adresses = [commande.origine.lower(), commande.destination.lower()]
            
            for zone, mots_cles in zones_mapping.items():
                for adresse in adresses:
                    for mot_cle in mots_cles:
                        if mot_cle in adresse:
                            zones[zone].append(commande)
                            zone_trouvee = True
                            break
                    if zone_trouvee:
                        break
                if zone_trouvee:
                    break
            
            if not zone_trouvee:
                zones['autres'].append(commande)
        
        # Retourner seulement les zones non vides
        return {zone: cmds for zone, cmds in zones.items() if cmds}
    
    @staticmethod
    def repartir_commandes_vehicules(commandes: List[Commande], 
                                   vehicules: List[Vehicule],
                                   date_debut: datetime,
                                   planificateur_id: int = None) -> List[Dict]:
        """Répartit intelligemment les commandes entre les véhicules disponibles"""
        tournees = []
        commandes_restantes = commandes.copy()
        
        # Trier les véhicules par capacité décroissante pour optimiser l'utilisation
        vehicules_tries = sorted(vehicules, key=lambda v: float(v.capacite_max), reverse=True)
        
        for vehicule in vehicules_tries:
            if not commandes_restantes:
                break
            
            # Sélectionner les commandes adaptées à ce véhicule
            commandes_vehicule = []
            poids_actuel = 0
            
            # Trier les commandes par priorité, puis par proximité géographique
            commandes_triees = PlanificationService.trier_commandes_pour_vehicule(
                commandes_restantes, vehicule
            )
            
            for commande in commandes_triees.copy():
                nouveau_poids = poids_actuel + float(commande.poids)
                
                # Vérifier la capacité
                if nouveau_poids <= float(vehicule.capacite_max):
                    commandes_vehicule.append(commande)
                    poids_actuel = nouveau_poids
                    commandes_restantes.remove(commande)
                    
                    # Limiter le nombre de commandes par tournée selon le type de véhicule
                    max_commandes = PlanificationService.get_max_commandes_par_vehicule(vehicule)
                    if len(commandes_vehicule) >= max_commandes:
                        break
            
            if commandes_vehicule:
                # Créer la planification de la tournée avec optimisation
                planification = OptimisationService.planifier_tournee_intelligente(
                    commandes_vehicule, vehicule, date_debut
                )
                
                if planification and 'erreur' not in planification:
                    # Calculer le prix estimé de la tournée
                    prix_estime = PlanificationService.calculer_prix_tournee(
                        commandes_vehicule, planification['distance_totale']
                    )
                    
                    tournees.append({
                        'vehicule': vehicule,
                        'transporteur': vehicule.transporteur,
                        'commandes': commandes_vehicule,
                        'planification': planification,
                        'date_debut': date_debut,
                        'date_fin': planification['heure_fin'],
                        'prix_estime': prix_estime,
                        'taux_remplissage': (poids_actuel / float(vehicule.capacite_max)) * 100
                    })
                    
                    # Décaler l'heure de début pour le prochain véhicule (éviter les conflits)
                    date_debut += timedelta(minutes=45)
        
        return tournees
    
    @staticmethod
    def trier_commandes_pour_vehicule(commandes: List[Commande], vehicule: Vehicule) -> List[Commande]:
        """Trie les commandes par ordre de priorité pour un véhicule donné"""
        def score_commande(cmd):
            score = 0
            
            # Priorité principale
            priorite_scores = {'urgente': 1000, 'haute': 100, 'normale': 10, 'basse': 1}
            score += priorite_scores.get(cmd.priorite, 10)
            
            # Bonus si le poids correspond bien au véhicule
            poids_cmd = float(cmd.poids)
            capacite = float(vehicule.capacite_max)
            
            if vehicule.type_vehicule == 'camionnette' and poids_cmd <= 500:
                score += 20
            elif vehicule.type_vehicule == 'camion' and 500 < poids_cmd <= 2000:
                score += 20
            elif vehicule.type_vehicule == 'semi_remorque' and poids_cmd > 2000:
                score += 20
            
            # Malus pour les commandes anciennes (encourager le traitement rapide)
            age_jours = (timezone.now() - cmd.date_creation).days
            if age_jours > 2:
                score += age_jours * 5
            
            return score
        
        return sorted(commandes, key=score_commande, reverse=True)
    
    @staticmethod
    def get_max_commandes_par_vehicule(vehicule: Vehicule) -> int:
        """Retourne le nombre maximum de commandes selon le type de véhicule"""
        max_commandes = {
            'camionnette': 4,
            'camion': 6,
            'semi_remorque': 8
        }
        return max_commandes.get(vehicule.type_vehicule, 5)
    
    @staticmethod
    def calculer_prix_tournee(commandes: List[Commande], distance_totale: float) -> float:
        """Calcule le prix estimé d'une tournée"""
        prix_total = 0
        
        for commande in commandes:
            # Utiliser l'API pour calculer le prix individuel
            prix_cmd = TransportAPIService.calculate_estimated_price(
                distance_totale / len(commandes),  # Distance moyenne par commande
                float(commande.poids),
                commande.priorite
            )
            prix_total += float(prix_cmd)
            
            # Mettre à jour le prix de la commande
            commande.prix = prix_cmd
            commande.save(update_fields=['prix'])
        
        return prix_total
    
    @staticmethod
    def creer_tournee_db(tournee_info: Dict, planificateur_id: int = None) -> Tournee:
        """Crée une tournée en base de données à partir des informations planifiées"""
        vehicule = tournee_info['vehicule']
        transporteur = tournee_info['transporteur']
        commandes = tournee_info['commandes']
        planification = tournee_info['planification']
        
        # Créer la tournée
        nom_tournee = f"Tournée {vehicule.immatriculation} - {tournee_info['date_debut'].strftime('%d/%m/%Y')}"
        
        tournee = Tournee.objects.create(
            nom=nom_tournee,
            planificateur_id=planificateur_id,
            transporteur=transporteur,
            vehicule=vehicule,
            date_debut_prevue=tournee_info['date_debut'],
            date_fin_prevue=tournee_info['date_fin'],
            distance_totale=planification['distance_totale'],
            duree_prevue=planification['duree_totale'],
            optimisee=True,
            notes=f"Tournée créée automatiquement - {len(commandes)} commande(s) - Taux de remplissage: {tournee_info.get('taux_remplissage', 0):.1f}%"
        )
        
        # Créer les étapes
        for etape_info in planification['etapes']:
            EtapeTournee.objects.create(
                tournee=tournee,
                commande_id=etape_info.get('commande_id'),
                ordre=etape_info['ordre'],
                type_etape=etape_info['type'],
                adresse=etape_info['adresse'],
                latitude=etape_info.get('latitude'),
                longitude=etape_info.get('longitude'),
                heure_prevue=etape_info['heure_prevue'],
                duree_prevue=etape_info['duree'],
                distance_precedente=etape_info.get('distance_precedente', 0)
            )
        
        # Mettre à jour les commandes
        for commande in commandes:
            # Calculer l'heure de livraison planifiée basée sur les étapes
            etape_livraison = next(
                (e for e in planification['etapes'] 
                 if e.get('commande_id') == commande.id and e['type'] == 'livraison'),
                None
            )
            
            commande.statut = 'planifiee'
            commande.planificateur_id = planificateur_id
            commande.transporteur = transporteur
            commande.date_livraison_planifiee = etape_livraison['heure_prevue'] if etape_livraison else None
            commande.save()
            
            # Créer la livraison
            Livraison.objects.create(
                commande=commande,
                vehicule=vehicule,
                tournee=tournee,
                statut='en_attente'
            )
        
        # Marquer le véhicule comme non disponible pour cette période
        vehicule.disponible = False
        vehicule.save()
        
        # Notifications
        PlanificationService.envoyer_notifications_tournee(
            tournee, commandes, planificateur_id
        )
        
        return tournee
    
    @staticmethod
    def envoyer_notifications_tournee(tournee: Tournee, commandes: List[Commande], 
                                    planificateur_id: int = None):
        """Envoie les notifications liées à la création d'une tournée"""
        
        # Notifier le transporteur
        Notification.objects.create(
            utilisateur=tournee.transporteur,
            type_notification='tournee_creee',
            titre='Nouvelle tournée assignée',
            message=f'Une tournée de {len(commandes)} commande(s) vous a été assignée pour le {tournee.date_debut_prevue.strftime("%d/%m/%Y à %H:%M")}. Distance totale: {tournee.distance_totale}km.',
            tournee=tournee,
            priority='high'
        )
        
        # Notifier les clients
        for commande in commandes:
            etape_livraison = tournee.etapes.filter(
                commande=commande, 
                type_etape='livraison'
            ).first()
            
            heure_livraison = etape_livraison.heure_prevue.strftime('%H:%M') if etape_livraison else 'À déterminer'
            
            Notification.objects.create(
                utilisateur=commande.client,
                type_notification='commande_planifiee',
                titre='Commande planifiée',
                message=f'Votre commande #{commande.id} a été planifiée dans une tournée. Livraison prévue le {tournee.date_debut_prevue.strftime("%d/%m/%Y")} vers {heure_livraison}.',
                commande=commande,
                tournee=tournee
            )
        
        # Notifier les administrateurs
        admins = User.objects.filter(role='admin', is_active=True)
        for admin in admins:
            Notification.objects.create(
                utilisateur=admin,
                type_notification='system',
                titre='Tournée créée automatiquement',
                message=f'Tournée {tournee.nom} créée avec {len(commandes)} commandes. Transporteur: {tournee.transporteur.get_full_name()}.',
                tournee=tournee,
                priority='normal'
            )
    
    @staticmethod
    def replanifier_tournee(tournee_id: int, nouvelles_commandes: List[int] = None) -> Dict:
        """Replanifie une tournée existante avec de nouvelles commandes ou optimisations"""
        try:
            tournee = Tournee.objects.get(id=tournee_id)
            
            if tournee.statut not in ['planifiee']:
                return {
                    'success': False,
                    'message': 'Seules les tournées planifiées peuvent être replanifiées'
                }
            
            with transaction.atomic():
                # Récupérer les commandes actuelles
                etapes_commandes = tournee.etapes.filter(commande__isnull=False)
                commandes_actuelles = list(set([etape.commande for etape in etapes_commandes if etape.commande]))
                
                # Ajouter les nouvelles commandes si spécifiées
                if nouvelles_commandes:
                    nouvelles_cmd = Commande.objects.filter(
                        id__in=nouvelles_commandes,
                        statut='en_attente'
                    )
                    commandes_actuelles.extend(list(nouvelles_cmd))
                
                # Vérifier la capacité
                poids_total = sum([float(cmd.poids) for cmd in commandes_actuelles])
                if poids_total > float(tournee.vehicule.capacite_max):
                    return {
                        'success': False,
                        'message': f'Poids total ({poids_total}kg) dépasse la capacité du véhicule ({tournee.vehicule.capacite_max}kg)'
                    }
                
                # Supprimer les anciennes étapes
                ancienne_distance = float(tournee.distance_totale or 0)
                ancienne_duree = tournee.duree_prevue
                tournee.etapes.all().delete()
                
                # Replanifier avec optimisation
                nouvelle_planification = OptimisationService.planifier_tournee_intelligente(
                    commandes_actuelles,
                    tournee.vehicule,
                    tournee.date_debut_prevue
                )
                
                if 'erreur' in nouvelle_planification:
                    return {
                        'success': False,
                        'message': nouvelle_planification['erreur']
                    }
                
                # Recréer les étapes optimisées
                for etape_info in nouvelle_planification['etapes']:
                    EtapeTournee.objects.create(
                        tournee=tournee,
                        commande_id=etape_info.get('commande_id'),
                        ordre=etape_info['ordre'],
                        type_etape=etape_info['type'],
                        adresse=etape_info['adresse'],
                        latitude=etape_info.get('latitude'),
                        longitude=etape_info.get('longitude'),
                        heure_prevue=etape_info['heure_prevue'],
                        duree_prevue=etape_info['duree'],
                        distance_precedente=etape_info.get('distance_precedente', 0)
                    )
                
                # Mettre à jour la tournée
                tournee.distance_totale = nouvelle_planification['distance_totale']
                tournee.date_fin_prevue = nouvelle_planification['heure_fin']
                tournee.duree_prevue = nouvelle_planification['duree_totale']
                tournee.optimisee = True
                tournee.notes += f" | Replanifiée le {timezone.now().strftime('%d/%m/%Y à %H:%M')}"
                tournee.save()
                
                # Mettre à jour les nouvelles commandes
                if nouvelles_commandes:
                    for cmd in nouvelles_cmd:
                        cmd.statut = 'planifiee'
                        cmd.transporteur = tournee.transporteur
                        cmd.planificateur = tournee.planificateur
                        cmd.save()
                        
                        # Créer la livraison
                        Livraison.objects.create(
                            commande=cmd,
                            vehicule=tournee.vehicule,
                            tournee=tournee,
                            statut='en_attente'
                        )
                
                # Calculer les gains
                gain_distance = ancienne_distance - nouvelle_planification['distance_totale']
                gain_pourcentage = (gain_distance / ancienne_distance * 100) if ancienne_distance > 0 else 0
                
                gain_temps = (ancienne_duree - nouvelle_planification['duree_totale']).total_seconds() / 3600 if ancienne_duree else 0
                
                # Notifier le transporteur
                Notification.objects.create(
                    utilisateur=tournee.transporteur,
                    type_notification='tournee_modifiee',
                    titre='Tournée modifiée',
                    message=f'Votre tournée {tournee.nom} a été replanifiée. Nouvelles informations disponibles.',
                    tournee=tournee,
                    priority='high'
                )
                
                return {
                    'success': True,
                    'message': 'Tournée replanifiée avec succès',
                    'ancienne_distance': ancienne_distance,
                    'nouvelle_distance': nouvelle_planification['distance_totale'],
                    'gain_distance': round(gain_distance, 2),
                    'gain_pourcentage': round(gain_pourcentage, 1),
                    'gain_temps_heures': round(gain_temps, 2),
                    'nouvelle_duree': nouvelle_planification['duree_totale'],
                    'nb_etapes': nouvelle_planification['nb_etapes'],
                    'nb_commandes': len(commandes_actuelles)
                }
                    
        except Tournee.DoesNotExist:
            return {'success': False, 'message': 'Tournée introuvable'}
        except Exception as e:
            return {'success': False, 'message': f'Erreur lors de la replanification: {str(e)}'}
    
    @staticmethod
    def suggerer_regroupements(date_cible: datetime = None) -> List[Dict]:
        """Suggère des regroupements de commandes pour optimiser les tournées"""
        if not date_cible:
            date_cible = timezone.now().date()
        
        # Récupérer les commandes en attente
        commandes = Commande.objects.filter(
            statut='en_attente',
            date_livraison_prevue__date=date_cible
        ).select_related('client')
        
        if not commandes.exists():
            return []
        
        # Grouper par zones géographiques
        zones_commandes = PlanificationService.grouper_par_zones(list(commandes))
        
        suggestions = []
        
        for zone, commandes_zone in zones_commandes.items():
            if len(commandes_zone) < 2:
                continue
            
            # Analyser les possibilités de regroupement
            groupes_possibles = PlanificationService.analyser_regroupements(commandes_zone)
            
            for groupe in groupes_possibles:
                if len(groupe['commandes']) >= 2:
                    suggestions.append({
                        'zone': zone,
                        'commandes': groupe['commandes'],
                        'poids_total': groupe['poids_total'],
                        'vehicule_recommande': groupe['vehicule_recommande'],
                        'economies_estimees': groupe['economies_estimees'],
                        'score_optimisation': groupe['score'],
                        'taux_remplissage': groupe.get('taux_charge', 0),
                        'urgence': any(cmd.priorite == 'urgente' for cmd in groupe['commandes'])
                    })
        
        # Trier par score d'optimisation décroissant, puis par urgence
        suggestions.sort(key=lambda x: (x['urgence'], x['score_optimisation']), reverse=True)
        
        return suggestions[:15]  # Retourner les 15 meilleures suggestions
    
    @staticmethod
    def analyser_regroupements(commandes: List[Commande]) -> List[Dict]:
        """Analyse les possibilités de regroupement pour une liste de commandes"""
        if len(commandes) < 2:
            return []
        
        groupes = []
        
        # Essayer différentes combinaisons
        from itertools import combinations
        
        # Tester les groupes de 2 à 6 commandes
        for taille_groupe in range(2, min(7, len(commandes) + 1)):
            for combo in combinations(commandes, taille_groupe):
                combo_list = list(combo)
                
                # Calculer les métriques du groupe
                poids_total = sum([float(cmd.poids) for cmd in combo_list])
                
                # Déterminer le véhicule recommandé
                vehicule_info = PlanificationService.determiner_vehicule_optimal(poids_total)
                
                # Vérifier si le groupe est viable
                if poids_total > vehicule_info['capacite_max']:
                    continue
                
                # Calculer le score d'optimisation
                score = PlanificationService.calculer_score_regroupement(combo_list)
                
                # Estimer les économies
                economies = PlanificationService.estimer_economies(combo_list)
                
                groupes.append({
                    'commandes': combo_list,
                    'poids_total': poids_total,
                    'vehicule_recommande': vehicule_info['type'],
                    'taux_charge': (poids_total / vehicule_info['capacite_max']) * 100,
                    'economies_estimees': economies,
                    'score': score
                })
        
        # Filtrer les groupes avec un score minimum
        groupes_viables = [g for g in groupes if g['score'] >= 65]
        
        # Trier par score décroissant
        groupes_viables.sort(key=lambda x: x['score'], reverse=True)
        
        return groupes_viables[:8]  # Retourner les 8 meilleurs groupes
    
    @staticmethod
    def determiner_vehicule_optimal(poids_total: float) -> Dict:
        """Détermine le type de véhicule optimal pour un poids donné"""
        if poids_total <= 1000:
            return {'type': 'camionnette', 'capacite_max': 1000}
        elif poids_total <= 5000:
            return {'type': 'camion', 'capacite_max': 5000}
        else:
            return {'type': 'semi_remorque', 'capacite_max': 15000}
    
    @staticmethod
    def calculer_score_regroupement(commandes: List[Commande]) -> float:
        """Calcule un score d'optimisation pour un regroupement de commandes"""
        if len(commandes) < 2:
            return 0
        
        score = 0
        
        # Facteur 1: Proximité géographique (35% du score)
        distances = []
        for i, cmd1 in enumerate(commandes):
            for cmd2 in commandes[i+1:]:
                # Distance entre origines
                coord1_orig = OptimisationService.geocoder_adresse_simple(cmd1.origine)
                coord2_orig = OptimisationService.geocoder_adresse_simple(cmd2.origine)
                dist_orig = OptimisationService.calculer_distance_haversine(
                    coord1_orig[0], coord1_orig[1], coord2_orig[0], coord2_orig[1]
                )
                
                # Distance entre destinations
                coord1_dest = OptimisationService.geocoder_adresse_simple(cmd1.destination)
                coord2_dest = OptimisationService.geocoder_adresse_simple(cmd2.destination)
                dist_dest = OptimisationService.calculer_distance_haversine(
                    coord1_dest[0], coord1_dest[1], coord2_dest[0], coord2_dest[1]
                )
                
                distances.append((dist_orig + dist_dest) / 2)
        
        if distances:
            distance_moyenne = sum(distances) / len(distances)
            if distance_moyenne <= 15:
                score += 35
            elif distance_moyenne <= 35:
                score += 25
            elif distance_moyenne <= 60:
                score += 15
            else:
                score += 5
        
        # Facteur 2: Compatibilité temporelle (25% du score)
        dates_livraison = [cmd.date_livraison_prevue for cmd in commandes]
        ecart_max = max(dates_livraison) - min(dates_livraison)
        
        if ecart_max.days == 0:
            score += 25  # Même jour
        elif ecart_max.days <= 1:
            score += 18  # Écart d'un jour
        elif ecart_max.days <= 2:
            score += 12  # Écart de deux jours
        else:
            score += 5   # Écart important
        
        # Facteur 3: Optimisation de la charge (20% du score)
        poids_total = sum([float(cmd.poids) for cmd in commandes])
        vehicule_info = PlanificationService.determiner_vehicule_optimal(poids_total)
        taux_remplissage = (poids_total / vehicule_info['capacite_max']) * 100
        
        if 70 <= taux_remplissage <= 90:
            score += 20  # Utilisation optimale
        elif 50 <= taux_remplissage <= 95:
            score += 15  # Bonne utilisation
        elif 30 <= taux_remplissage <= 50:
            score += 10  # Utilisation acceptable
        else:
            score += 5   # Utilisation sous-optimale
        
        # Facteur 4: Priorités compatibles (12% du score)
        priorites = [cmd.priorite for cmd in commandes]
        if 'urgente' in priorites:
            if all(p in ['urgente', 'haute'] for p in priorites):
                score += 12  # Toutes prioritaires
            elif len([p for p in priorites if p == 'urgente']) == 1:
                score += 8   # Une seule urgente
            else:
                score += 6   # Mélange avec urgentes
        elif len(set(priorites)) == 1:
            score += 10  # Toutes les commandes ont la même priorité
        else:
            score += 8   # Priorités mixtes acceptables
        
        # Facteur 5: Nombre de commandes (8% du score)
        nb_commandes = len(commandes)
        if nb_commandes == 3 or nb_commandes == 4:
            score += 8   # Nombre optimal
        elif nb_commandes == 2 or nb_commandes == 5:
            score += 6   # Acceptable
        else:
            score += 4   # Autres cas
        
        return min(100, max(0, score))  # Score entre 0 et 100
    
    @staticmethod
    def estimer_economies(commandes: List[Commande]) -> Dict:
        """Estime les économies réalisées en regroupant des commandes"""
        if len(commandes) < 2:
            return {'distance': 0, 'temps': 0, 'cout': 0}
        
        # Calcul séparé (chaque commande dans sa propre tournée)
        distance_separee = 0
        temps_separe = 0
        cout_separe = 0
        
        depot_coords = (33.5731, -7.5898)  # Casablanca
        
        for cmd in commandes:
            # Calculer la distance pour une livraison individuelle
            coord_orig = OptimisationService.geocoder_adresse_simple(cmd.origine)
            coord_dest = OptimisationService.geocoder_adresse_simple(cmd.destination)
            
            dist_depot_orig = OptimisationService.calculer_distance_haversine(
                depot_coords[0], depot_coords[1], coord_orig[0], coord_orig[1]
            )
            dist_orig_dest = OptimisationService.calculer_distance_haversine(
                coord_orig[0], coord_orig[1], coord_dest[0], coord_dest[1]
            )
            dist_dest_depot = OptimisationService.calculer_distance_haversine(
                coord_dest[0], coord_dest[1], depot_coords[0], depot_coords[1]
            )
            
            distance_cmd = dist_depot_orig + dist_orig_dest + dist_dest_depot
            distance_separee += distance_cmd
            
            # Temps estimé (40 km/h moyenne + temps de service)
            temps_cmd = (distance_cmd / 40) + 1.5  # 1.5h de service
            temps_separe += temps_cmd
            
            # Coût estimé
            cout_cmd = float(TransportAPIService.calculate_estimated_price(
                distance_cmd, float(cmd.poids), cmd.priorite
            ))
            cout_separe += cout_cmd
        
        # Calcul groupé (simulation d'optimisation)
        # Les économies varient selon le nombre de commandes et leur proximité
        facteur_economie_distance = 0.25 + (0.05 * len(commandes))  # 25-40% d'économie
        facteur_economie_temps = 0.20 + (0.04 * len(commandes))     # 20-35% d'économie
        facteur_economie_cout = 0.15 + (0.03 * len(commandes))      # 15-30% d'économie
        
        # Limiter les facteurs d'économie
        facteur_economie_distance = min(0.5, facteur_economie_distance)
        facteur_economie_temps = min(0.45, facteur_economie_temps)
        facteur_economie_cout = min(0.35, facteur_economie_cout)
        
        # Calculer les économies
        economie_distance = distance_separee * facteur_economie_distance
        economie_temps = temps_separe * facteur_economie_temps
        economie_cout = cout_separe * facteur_economie_cout
        
        return {
            'distance': round(economie_distance, 1),
            'temps': round(economie_temps, 2),  # en heures
            'cout': round(economie_cout, 2),
            'pourcentage_distance': round(facteur_economie_distance * 100, 1),
            'pourcentage_temps': round(facteur_economie_temps * 100, 1),
            'pourcentage_cout': round(facteur_economie_cout * 100, 1),
            'economies_co2': round(economie_distance * 0.25, 2)  # kg CO2 économisés (estimation)
        }
    
    @staticmethod
    def generer_rapport_planification(date_debut: datetime, date_fin: datetime, 
                                    planificateur_id: int = None) -> Dict:
        """Génère un rapport détaillé de la planification sur une période"""
        
        # Filtres de base
        tournees_filter = Tournee.objects.filter(
            date_creation__range=[date_debut, date_fin]
        )
        
        if planificateur_id:
            tournees_filter = tournees_filter.filter(planificateur_id=planificateur_id)
        
        tournees = tournees_filter.select_related('transporteur', 'vehicule', 'planificateur')
        
        # Métriques générales
        nb_tournees = tournees.count()
        nb_commandes_planifiees = Commande.objects.filter(
            etapes_tournee__tournee__in=tournees
        ).distinct().count()
        
        # Répartition par statut
        repartition_statuts = {}
        for statut, label in Tournee.STATUS_CHOICES:
            count = tournees.filter(statut=statut).count()
            repartition_statuts[label] = count
        
        # Performance des transporteurs
        transporteurs_stats = {}
        for tournee in tournees:
            transporteur = tournee.transporteur.get_full_name()
            if transporteur not in transporteurs_stats:
                transporteurs_stats[transporteur] = {
                    'nb_tournees': 0,
                    'nb_commandes': 0,
                    'distance_totale': 0,
                    'taux_reussite': 0,
                    'revenus_estimes': 0
                }
            
            transporteurs_stats[transporteur]['nb_tournees'] += 1
            transporteurs_stats[transporteur]['nb_commandes'] += tournee.nb_commandes
            transporteurs_stats[transporteur]['distance_totale'] += float(tournee.distance_totale or 0)
            
            # Calculer les revenus estimés
            commandes_tournee = Commande.objects.filter(etapes_tournee__tournee=tournee)
            revenus_tournee = sum([float(cmd.prix or 0) for cmd in commandes_tournee])
            transporteurs_stats[transporteur]['revenus_estimes'] += revenus_tournee
        
        # Calculer le taux de réussite pour chaque transporteur
        for transporteur, stats in transporteurs_stats.items():
            tournees_transporteur = tournees.filter(transporteur__first_name__icontains=transporteur.split()[0])
            tournees_reussies = tournees_transporteur.filter(statut='terminee').count()
            if stats['nb_tournees'] > 0:
                stats['taux_reussite'] = round((tournees_reussies / stats['nb_tournees']) * 100, 1)
        
        # Efficacité de planification
        tournees_optimisees = tournees.filter(optimisee=True).count()
        taux_optimisation = (tournees_optimisees / nb_tournees * 100) if nb_tournees > 0 else 0
        
        # Utilisation des véhicules
        vehicules_utilises = tournees.values('vehicule').distinct().count()
        vehicules_totaux = Vehicule.objects.filter(disponible=True).count()
        taux_utilisation_vehicules = (vehicules_utilises / vehicules_totaux * 100) if vehicules_totaux > 0 else 0
        
        # Analyse des retards
        tournees_terminees = tournees.filter(statut='terminee', date_fin_reelle__isnull=False)
        retards = []
        for tournee in tournees_terminees:
            if tournee.date_fin_prevue and tournee.date_fin_reelle:
                retard_heures = (tournee.date_fin_reelle - tournee.date_fin_prevue).total_seconds() / 3600
                retards.append(retard_heures)
        
        retard_moyen = round(sum(retards) / len(retards), 2) if retards else 0
        pourcentage_en_retard = round((len([r for r in retards if r > 0]) / len(retards) * 100), 1) if retards else 0
        
        # Économies réalisées (estimation)
        distance_totale_planifiee = sum([float(t.distance_totale or 0) for t in tournees])
        economies_distance = round(distance_totale_planifiee * 0.20, 1)  # 20% d'économie estimée
        economies_temps = round(nb_tournees * 2.8, 1)  # 2.8h économisées par tournée optimisée
        economies_cout = round(nb_tournees * 150, 2)  # 150 DH économisés par tournée
        economies_co2 = round(economies_distance * 0.25, 2)  # kg CO2 économisés
        
        # Top des meilleures tournées
        meilleures_tournees = []
        for tournee in tournees:
            efficacite = OptimisationService.calculer_efficacite_tournee(tournee)
            if 'score_optimisation' in efficacite:
                meilleures_tournees.append({
                    'tournee': tournee,
                    'score': efficacite['score_optimisation'],
                    'taux_remplissage': efficacite.get('taux_remplissage', 0)
                })
        
        meilleures_tournees.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'periode': {
                'debut': date_debut,
                'fin': date_fin,
                'duree_jours': (date_fin - date_debut).days + 1
            },
            'metriques_generales': {
                'nb_tournees': nb_tournees,
                'nb_commandes_planifiees': nb_commandes_planifiees,
                'moyenne_commandes_par_tournee': round(nb_commandes_planifiees / nb_tournees, 1) if nb_tournees > 0 else 0,
                'taux_optimisation': round(taux_optimisation, 1),
                'taux_utilisation_vehicules': round(taux_utilisation_vehicules, 1),
                'retard_moyen_heures': retard_moyen,
                'pourcentage_en_retard': pourcentage_en_retard
            },
            'repartition_statuts': repartition_statuts,
            'performance_transporteurs': transporteurs_stats,
            'total_distance_planifiee': round(distance_totale_planifiee, 1),
            'economies_estimees': {
                'distance_km': economies_distance,
                'temps_heures': economies_temps,
                'cout_dh': economies_cout,
                'co2_kg': economies_co2
            },
            'meilleures_tournees': meilleures_tournees[:5],  # Top 5
            'recommandations': PlanificationService.generer_recommandations(
                tournees, transporteurs_stats, taux_optimisation
            )
        }
    
    @staticmethod
    def generer_recommandations(tournees, transporteurs_stats: Dict, 
                               taux_optimisation: float) -> List[str]:
        """Génère des recommandations d'amélioration"""
        recommandations = []
        
        # Recommandations basées sur l'optimisation
        if taux_optimisation < 70:
            recommandations.append(
                f"Taux d'optimisation faible ({taux_optimisation:.1f}%) - "
                "Utiliser davantage la planification automatique"
            )
        elif taux_optimisation > 95:
            recommandations.append(
                "Excellent taux d'optimisation - Maintenir les bonnes pratiques"
            )
        
        # Recommandations basées sur les performances des transporteurs
        if transporteurs_stats:
            performances = [stats['taux_reussite'] for stats in transporteurs_stats.values()]
            perf_moyenne = sum(performances) / len(performances) if performances else 0
            
            if perf_moyenne < 80:
                recommandations.append(
                    f"Taux de réussite moyen faible ({perf_moyenne:.1f}%) - "
                    "Former les transporteurs ou revoir les plannings"
                )
            
            # Identifier les transporteurs en difficulté
            transporteurs_faibles = [
                nom for nom, stats in transporteurs_stats.items() 
                if stats['taux_reussite'] < 70 and stats['nb_tournees'] > 2
            ]
            
            if transporteurs_faibles:
                recommandations.append(
                    f"Transporteurs nécessitant un accompagnement: "
                    f"{', '.join(transporteurs_faibles[:3])}"
                )
        
        # Recommandations basées sur l'utilisation des véhicules
        nb_tournees = tournees.count()
        if nb_tournees > 0:
            tournees_par_vehicule = {}
            for tournee in tournees:
                vehicule_id = tournee.vehicule.id
                tournees_par_vehicule[vehicule_id] = tournees_par_vehicule.get(vehicule_id, 0) + 1
            
            if tournees_par_vehicule:
                utilisation_moyenne = sum(tournees_par_vehicule.values()) / len(tournees_par_vehicule)
                if utilisation_moyenne < 2:
                    recommandations.append(
                        "Faible utilisation des véhicules - "
                        "Optimiser la répartition ou réduire la flotte"
                    )
        
        # Recommandations générales
        if nb_tournees == 0:
            recommandations.append("Aucune tournée planifiée - Vérifier les commandes en attente")
        elif nb_tournees < 5:
            recommandations.append("Peu de tournées - Envisager la planification groupée")
        
        if not recommandations:
            recommandations.append("Performance globale satisfaisante - Continuer les bonnes pratiques")
        
        return recommandations
    
    @staticmethod
    def planification_urgence(commande_id: int, planificateur_id: int = None) -> Dict:
        """Planifie une commande urgente en priorité"""
        try:
            commande = Commande.objects.get(id=commande_id)
            
            if commande.statut != 'en_attente':
                return {
                    'success': False,
                    'message': 'Seules les commandes en attente peuvent être planifiées'
                }
            
            # Marquer comme urgente si ce n'est pas déjà fait
            if commande.priorite != 'urgente':
                commande.priorite = 'urgente'
                commande.save()
            
            # Chercher un véhicule immédiatement disponible
            vehicules_disponibles = Vehicule.objects.filter(
                disponible=True,
                transporteur__is_active=True
            ).select_related('transporteur')
            
            if not vehicules_disponibles.exists():
                return {
                    'success': False,
                    'message': 'Aucun véhicule disponible pour la planification urgente'
                }
            
            # Sélectionner le véhicule le plus adapté
            vehicule_optimal = None
            poids_commande = float(commande.poids)
            
            for vehicule in vehicules_disponibles:
                if poids_commande <= float(vehicule.capacite_max):
                    vehicule_optimal = vehicule
                    break
            
            if not vehicule_optimal:
                return {
                    'success': False,
                    'message': 'Aucun véhicule avec la capacité suffisante'
                }
            
            # Créer une tournée urgente
            heure_debut = timezone.now() + timedelta(minutes=30)  # Départ dans 30 min
            
            planification = OptimisationService.planifier_tournee_intelligente(
                [commande], vehicule_optimal, heure_debut
            )
            
            if 'erreur' in planification:
                return {
                    'success': False,
                    'message': planification['erreur']
                }
            
            # Créer la tournée urgente
            tournee_info = {
                'vehicule': vehicule_optimal,
                'transporteur': vehicule_optimal.transporteur,
                'commandes': [commande],
                'planification': planification,
                'date_debut': heure_debut,
                'date_fin': planification['heure_fin'],
                'prix_estime': float(TransportAPIService.calculate_estimated_price(
                    planification['distance_totale'], poids_commande, 'urgente'
                )),
                'taux_remplissage': (poids_commande / float(vehicule_optimal.capacite_max)) * 100
            }
            
            with transaction.atomic():
                tournee = PlanificationService.creer_tournee_db(tournee_info, planificateur_id)
                tournee.nom = f"URGENTE - {tournee.nom}"
                tournee.save()
                
                # Notifications urgentes
                Notification.objects.create(
                    utilisateur=tournee.transporteur,
                    type_notification='tournee_urgente',
                    titre='TOURNÉE URGENTE ASSIGNÉE',
                    message=f'Tournée urgente pour la commande #{commande.id}. Départ prévu dans 30 minutes!',
                    tournee=tournee,
                    priority='urgent'
                )
                
                return {
                    'success': True,
                    'message': 'Tournée urgente créée avec succès',
                    'tournee_id': tournee.id,
                    'transporteur': tournee.transporteur.get_full_name(),
                    'heure_depart': heure_debut,
                    'heure_livraison_prevue': planification['heure_fin'],
                    'distance_totale': planification['distance_totale']
                }
                
        except Commande.DoesNotExist:
            return {'success': False, 'message': 'Commande introuvable'}
        except Exception as e:
            return {'success': False, 'message': f'Erreur planification urgente: {str(e)}'}
    
    @staticmethod
    def analyser_capacite_planification(date_cible: datetime = None) -> Dict:
        """Analyse la capacité de planification pour une date donnée"""
        if not date_cible:
            date_cible = timezone.now().date()
        
        # Commandes à planifier
        commandes_en_attente = Commande.objects.filter(
            statut='en_attente',
            date_livraison_prevue__date=date_cible
        )
        
        # Véhicules disponibles
        vehicules_disponibles = Vehicule.objects.filter(
            disponible=True,
            transporteur__is_active=True
        )
        
        # Tournées déjà planifiées
        tournees_planifiees = Tournee.objects.filter(
            date_debut_prevue__date=date_cible,
            statut__in=['planifiee', 'en_cours']
        )
        
        # Calculer la charge de travail
        poids_total_attente = sum([float(cmd.poids) for cmd in commandes_en_attente])
        capacite_totale_disponible = sum([float(v.capacite_max) for v in vehicules_disponibles])
        
        # Analyser les véhicules occupés
        vehicules_occupes = tournees_planifiees.values_list('vehicule_id', flat=True)
        vehicules_libres = vehicules_disponibles.exclude(id__in=vehicules_occupes)
        capacite_reellement_disponible = sum([float(v.capacite_max) for v in vehicules_libres])
        
        # Calculer le taux d'occupation
        taux_occupation = 0
        if capacite_reellement_disponible > 0:
            taux_occupation = (poids_total_attente / capacite_reellement_disponible) * 100
        
        # Déterminer le statut de capacité
        if taux_occupation <= 70:
            statut_capacite = 'EXCELLENTE'
            couleur = 'success'
        elif taux_occupation <= 85:
            statut_capacite = 'BONNE'
            couleur = 'info'
        elif taux_occupation <= 100:
            statut_capacite = 'LIMITE'
            couleur = 'warning'
        else:
            statut_capacite = 'INSUFFISANTE'
            couleur = 'danger'
        
        # Suggestions d'amélioration
        suggestions = []
        if taux_occupation > 100:
            suggestions.append('Capacité insuffisante - Acquérir des véhicules supplémentaires')
            suggestions.append('Reporter certaines commandes non urgentes')
        elif taux_occupation > 85:
            suggestions.append('Capacité limite - Optimiser les tournées')
            suggestions.append('Prioriser les commandes urgentes')
        elif taux_occupation < 50:
            suggestions.append('Sous-utilisation - Accepter plus de commandes')
            suggestions.append('Optimiser l\'utilisation des véhicules')
        
        return {
            'date_analyse': date_cible,
            'commandes_en_attente': commandes_en_attente.count(),
            'poids_total_attente': round(poids_total_attente, 1),
            'vehicules_disponibles': vehicules_disponibles.count(),
            'vehicules_libres': vehicules_libres.count(),
            'capacite_totale': round(capacite_totale_disponible, 1),
            'capacite_disponible': round(capacite_reellement_disponible, 1),
            'taux_occupation': round(taux_occupation, 1),
            'statut_capacite': statut_capacite,
            'couleur_statut': couleur,
            'tournees_planifiees': tournees_planifiees.count(),
            'suggestions': suggestions,
            'peut_planifier_auto': taux_occupation <= 95,
            'commandes_urgentes': commandes_en_attente.filter(priorite='urgente').count()
        }