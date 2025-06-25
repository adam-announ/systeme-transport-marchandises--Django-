# Nouveau fichier: utilisateurs/services/planification_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum
from ..models import (
    Commande, Vehicule, User, Tournee, EtapeTournee, 
    Livraison, Notification
)
from .optimisation_service import OptimisationService

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
        
        # Récupérer les commandes en attente
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
        
        # Grouper les commandes par zones géographiques
        zones_commandes = PlanificationService.grouper_par_zones(list(commandes_disponibles))
        
        tournees_creees = []
        commandes_traitees = []
        
        try:
            with transaction.atomic():
                for zone, commandes_zone in zones_commandes.items():
                    # Répartir les commandes de cette zone entre les véhicules disponibles
                    tournees_zone = PlanificationService.repartir_commandes_vehicules(
                        commandes_zone, 
                        list(vehicules_disponibles),
                        date_cible,
                        planificateur_id
                    )
                    
                    tournees_creees.extend(tournees_zone)
                    commandes_traitees.extend([cmd for tournee in tournees_zone 
                                             for cmd in tournee['commandes']])
                    
                    # Marquer les véhicules utilisés comme non disponibles
                    vehicules_utilises = [t['vehicule'].id for t in tournees_zone]
                    vehicules_disponibles = vehicules_disponibles.exclude(id__in=vehicules_utilises)
                    
                    if not vehicules_disponibles.exists():
                        break
                
                # Créer les tournées en base de données
                tournees_db = []
                for tournee_info in tournees_creees:
                    tournee_db = PlanificationService.creer_tournee_db(
                        tournee_info, planificateur_id
                    )
                    tournees_db.append(tournee_db)
                
                return {
                    'success': True,
                    'message': f'{len(tournees_creees)} tournée(s) créée(s) avec succès',
                    'tournees_creees': len(tournees_creees),
                    'commandes_traitees': len(commandes_traitees),
                    'commandes_restantes': commandes_disponibles.count() - len(commandes_traitees),
                    'tournees': tournees_db
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la planification: {str(e)}',
                'tournees_creees': 0
            }
    
    @staticmethod
    def grouper_par_zones(commandes: List[Commande]) -> Dict[str, List[Commande]]:
        """Groupe les commandes par zones géographiques"""
        zones = {
            'casablanca': [],
            'rabat': [],
            'marrakech': [],
            'fes': [],
            'tanger': [],
            'autres': []
        }
        
        for commande in commandes:
            zone_trouvee = False
            
            # Analyser l'origine et la destination
            adresses = [commande.origine.lower(), commande.destination.lower()]
            
            for adresse in adresses:
                for zone in zones.keys():
                    if zone != 'autres' and zone in adresse:
                        zones[zone].append(commande)
                        zone_trouvee = True
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
        """Répartit les commandes entre les véhicules disponibles"""
        tournees = []
        commandes_restantes = commandes.copy()
        
        for vehicule in vehicules:
            if not commandes_restantes:
                break
            
            # Sélectionner les commandes adaptées à ce véhicule
            commandes_vehicule = []
            poids_actuel = 0
            
            # Trier par priorité puis par proximité
            commandes_triees = sorted(
                commandes_restantes,
                key=lambda x: (x.priorite != 'urgente', x.priorite != 'haute', x.date_creation)
            )
            
            for commande in commandes_triees.copy():
                if poids_actuel + float(commande.poids) <= float(vehicule.capacite_max):
                    commandes_vehicule.append(commande)
                    poids_actuel += float(commande.poids)
                    commandes_restantes.remove(commande)
                    
                    # Limiter le nombre de commandes par tournée
                    if len(commandes_vehicule) >= 8:  # Max 8 commandes par tournée
                        break
            
            if commandes_vehicule:
                # Créer la planification de la tournée
                planification = OptimisationService.planifier_tournee_intelligente(
                    commandes_vehicule, vehicule, date_debut
                )
                
                if planification and 'erreur' not in planification:
                    tournees.append({
                        'vehicule': vehicule,
                        'transporteur': vehicule.transporteur,
                        'commandes': commandes_vehicule,
                        'planification': planification,
                        'date_debut': date_debut,
                        'date_fin': planification['heure_fin']
                    })
                    
                    # Décaler l'heure de début pour le prochain véhicule
                    date_debut += timedelta(minutes=30)
        
        return tournees
    
    @staticmethod
    def creer_tournee_db(tournee_info: Dict, planificateur_id: int = None) -> Tournee:
        """Crée une tournée en base de données à partir des informations planifiées"""
        vehicule = tournee_info['vehicule']
        transporteur = tournee_info['transporteur']
        commandes = tournee_info['commandes']
        planification = tournee_info['planification']
        
        # Créer la tournée
        nom_tournee = f"Tournée {vehicule.immatriculation} - {planification['heure_fin'].strftime('%d/%m/%Y')}"
        
        tournee = Tournee.objects.create(
            nom=nom_tournee,
            planificateur_id=planificateur_id,
            transporteur=transporteur,
            vehicule=vehicule,
            date_debut_prevue=tournee_info['date_debut'],
            date_fin_prevue=tournee_info['date_fin'],
            distance_totale=planification['distance_totale'],
            duree_totale_estimee=planification['duree_totale'],
            optimisee=True,
            notes=f"Tournée créée automatiquement - {len(commandes)} commande(s)"
        )
        
        # Créer les étapes
        for i, etape_info in enumerate(planification['etapes']):
            EtapeTournee.objects.create(
                tournee=tournee,
                commande_id=etape_info.get('commande_id'),
                ordre=i + 1,
                type_etape=etape_info['type'],
                adresse=etape_info['adresse'],
                latitude=etape_info.get('latitude'),
                longitude=etape_info.get('longitude'),
                heure_prevue=etape_info['heure_prevue'],
                duree_prevue=etape_info['duree']
            )
        
        # Mettre à jour les commandes
        for commande in commandes:
            commande.statut = 'planifiee'
            commande.planificateur_id = planificateur_id
            commande.transporteur = transporteur
            commande.date_livraison_planifiee = None  # Sera calculé selon les étapes
            commande.save()
            
            # Créer la livraison
            Livraison.objects.create(
                commande=commande,
                vehicule=vehicule,
                tournee=tournee,
                statut='en_attente'
            )
        
        # Notifications
        if planificateur_id:
            planificateur = User.objects.get(id=planificateur_id)
            
            # Notifier le transporteur
            Notification.objects.create(
                utilisateur=transporteur,
                type_notification='tournee_creee',
                titre='Nouvelle tournée assignée',
                message=f'Une tournée de {len(commandes)} commande(s) vous a été assignée pour le {tournee.date_debut_prevue.strftime("%d/%m/%Y")}.',
                tournee=tournee,
                priority='high'
            )
            
            # Notifier les clients
            for commande in commandes:
                Notification.objects.create(
                    utilisateur=commande.client,
                    type_notification='commande_planifiee',
                    titre='Commande planifiée',
                    message=f'Votre commande #{commande.id} a été planifiée dans une tournée. Livraison prévue le {tournee.date_debut_prevue.strftime("%d/%m/%Y")}.',
                    commande=commande,
                    tournee=tournee
                )
        
        return tournee
    
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
                commandes_actuelles = list(Commande.objects.filter(
                    etapes_tournee__tournee=tournee
                ).distinct())
                
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
                
                # Supprimer les anciennes étapes (sauf dépôts)
                tournee.etapes.exclude(type_etape='depot').delete()
                
                # Replanifier avec les nouvelles commandes
                nouvelle_planification = OptimisationService.planifier_tournee_intelligente(
                    commandes_actuelles,
                    tournee.vehicule,
                    tournee.date_debut_prevue
                )
                
                if nouvelle_planification and 'erreur' not in nouvelle_planification:
                    # Mettre à jour la tournée
                    tournee.date_fin_prevue = nouvelle_planification['heure_fin']
                    tournee.distance_totale = nouvelle_planification['distance_totale']
                    tournee.duree_totale_estimee = nouvelle_planification['duree_totale']
                    tournee.optimisee = True
                    tournee.save()
                    
                    # Recréer les étapes
                    for i, etape_info in enumerate(nouvelle_planification['etapes']):
                        EtapeTournee.objects.create(
                            tournee=tournee,
                            commande_id=etape_info.get('commande_id'),
                            ordre=i + 1,
                            type_etape=etape_info['type'],
                            adresse=etape_info['adresse'],
                            latitude=etape_info.get('latitude'),
                            longitude=etape_info.get('longitude'),
                            heure_prevue=etape_info['heure_prevue'],
                            duree_prevue=etape_info['duree']
                        )
                    
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
                    
                    return {
                        'success': True,
                        'message': 'Tournée replanifiée avec succès',
                        'nouvelle_fin': nouvelle_planification['heure_fin'],
                        'distance_totale': nouvelle_planification['distance_totale'],
                        'nb_commandes': len(commandes_actuelles)
                    }
                else:
                    return {
                        'success': False,
                        'message': nouvelle_planification.get('erreur', 'Erreur de planification')
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la replanification: {str(e)}'
            }
    
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
                        'score_optimisation': groupe['score']
                    })
        
        # Trier par score d'optimisation décroissant
        suggestions.sort(key=lambda x: x['score_optimisation'], reverse=True)
        
        return suggestions[:10]  # Retourner les 10 meilleures suggestions
    
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
                if poids_total <= 1000:
                    vehicule_recommande = 'camionnette'
                    capacite_max = 1000
                elif poids_total <= 5000:
                    vehicule_recommande = 'camion'
                    capacite_max = 5000
                else:
                    vehicule_recommande = 'semi_remorque'
                    capacite_max = 15000
                
                # Vérifier si le groupe est viable
                if poids_total > capacite_max:
                    continue
                
                # Calculer le score d'optimisation
                score = PlanificationService.calculer_score_regroupement(combo_list)
                
                # Estimer les économies
                economies = PlanificationService.estimer_economies(combo_list)
                
                groupes.append({
                    'commandes': combo_list,
                    'poids_total': poids_total,
                    'vehicule_recommande': vehicule_recommande,
                    'taux_charge': (poids_total / capacite_max) * 100,
                    'economies_estimees': economies,
                    'score': score
                })
        
        # Filtrer les groupes avec un score minimum
        groupes_viables = [g for g in groupes if g['score'] >= 60]
        
        # Trier par score décroissant
        groupes_viables.sort(key=lambda x: x['score'], reverse=True)
        
        return groupes_viables[:5]  # Retourner les 5 meilleurs groupes
    
    @staticmethod
    def calculer_score_regroupement(commandes: List[Commande]) -> float:
        """Calcule un score d'optimisation pour un regroupement de commandes"""
        if len(commandes) < 2:
            return 0
        
        score = 0
        
        # Facteur 1: Proximité géographique (40% du score)
        coordonnees = []
        for cmd in commandes:
            lat_orig, lng_orig = OptimisationService.geocoder_adresse_simple(cmd.origine)
            lat_dest, lng_dest = OptimisationService.geocoder_adresse_simple(cmd.destination)
            coordonnees.extend([(lat_orig, lng_orig), (lat_dest, lng_dest)])
        
        if len(coordonnees) > 1:
            # Calculer la dispersion moyenne
            distances = []
            for i in range(len(coordonnees)):
                for j in range(i + 1, len(coordonnees)):
                    dist = OptimisationService.calculer_distance_haversine(
                        coordonnees[i][0], coordonnees[i][1],
                        coordonnees[j][0], coordonnees[j][1]
                    )
                    distances.append(dist)
            
            distance_moyenne = sum(distances) / len(distances) if distances else 100
            
            # Score inversement proportionnel à la distance (plus c'est proche, mieux c'est)
            if distance_moyenne <= 10:
                score += 40
            elif distance_moyenne <= 25:
                score += 30
            elif distance_moyenne <= 50:
                score += 20
            else:
                score += 10
        
        # Facteur 2: Compatibilité temporelle (25% du score)
        dates_livraison = [cmd.date_livraison_prevue for cmd in commandes]
        ecart_max = max(dates_livraison) - min(dates_livraison)
        
        if ecart_max.days == 0:
            score += 25  # Même jour
        elif ecart_max.days <= 1:
            score += 15  # Écart d'un jour
        elif ecart_max.days <= 3:
            score += 10  # Écart de quelques jours
        else:
            score += 5   # Écart important
        
        # Facteur 3: Optimisation de la charge (20% du score)
        poids_total = sum([float(cmd.poids) for cmd in commandes])
        
        # Score basé sur l'utilisation optimale des véhicules
        if 500 <= poids_total <= 900:  # Camionnette bien remplie
            score += 20
        elif 2000 <= poids_total <= 4500:  # Camion bien rempli
            score += 20
        elif 8000 <= poids_total <= 14000:  # Semi-remorque bien rempli
            score += 20
        elif poids_total < 500:
            score += 10  # Charge faible mais acceptable
        else:
            score += 15  # Autres cas
        
        # Facteur 4: Priorités compatibles (10% du score)
        priorites = [cmd.priorite for cmd in commandes]
        if len(set(priorites)) == 1:
            score += 10  # Toutes les commandes ont la même priorité
        elif 'urgente' in priorites and len([p for p in priorites if p != 'urgente']) > 0:
            score += 5   # Mélange avec urgente (moins optimal)
        else:
            score += 8   # Priorités compatibles
        
        # Facteur 5: Nombre de commandes (5% du score)
        if len(commandes) == 3 or len(commandes) == 4:
            score += 5   # Nombre optimal
        elif len(commandes) == 2:
            score += 4   # Acceptable
        else:
            score += 3   # Autres cas
        
        return min(100, max(0, score))  # Score entre 0 et 100
    
    @staticmethod
    def estimer_economies(commandes: List[Commande]) -> Dict:
        """Estime les économies réalisées en regroupant des commandes"""
        if len(commandes) < 2:
            return {'distance': 0, 'temps': 0, 'cout': 0}
        
        # Calcul séparé (chaque commande dans sa propre tournée)
        distance_separee = 0
        temps_separe = 0
        
        for cmd in commandes:
            # Distance aller-retour depuis le dépôt
            lat_orig, lng_orig = OptimisationService.geocoder_adresse_simple(cmd.origine)
            lat_dest, lng_dest = OptimisationService.geocoder_adresse_simple(cmd.destination)
            depot_coords = (33.5731, -7.5898)  # Casablanca
            
            dist_depot_orig = OptimisationService.calculer_distance_haversine(
                depot_coords[0], depot_coords[1], lat_orig, lng_orig
            )
            dist_orig_dest = OptimisationService.calculer_distance_haversine(
                lat_orig, lng_orig, lat_dest, lng_dest
            )
            dist_dest_depot = OptimisationService.calculer_distance_haversine(
                lat_dest, lng_dest, depot_coords[0], depot_coords[1]
            )
            
            distance_separee += dist_depot_orig + dist_orig_dest + dist_dest_depot
            temps_separe += distance_separee / 40 * 60  # 40 km/h moyenne, en minutes
        
        # Calcul groupé (simulation d'optimisation)
        distance_groupee = distance_separee * 0.7  # Estimation: 30% d'économie
        temps_groupe = temps_separe * 0.75  # Estimation: 25% d'économie
        
        # Économies
        economie_distance = distance_separee - distance_groupee
        economie_temps = temps_separe - temps_groupe
        economie_cout = economie_distance * 1.2 + (economie_temps / 60) * 25  # 1.2€/km + 25€/h
        
        return {
            'distance': round(economie_distance, 1),
            'temps': round(economie_temps, 1),  # en minutes
            'cout': round(economie_cout, 2),
            'pourcentage_distance': round((economie_distance / distance_separee) * 100, 1),
            'pourcentage_temps': round((economie_temps / temps_separe) * 100, 1)
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
                    'taux_reussite': 0
                }
            
            transporteurs_stats[transporteur]['nb_tournees'] += 1
            transporteurs_stats[transporteur]['nb_commandes'] += tournee.get_nb_commandes()
            transporteurs_stats[transporteur]['distance_totale'] += float(tournee.distance_totale or 0)
        
        # Efficacité de planification
        tournees_optimisees = tournees.filter(optimisee=True).count()
        taux_optimisation = (tournees_optimisees / nb_tournees * 100) if nb_tournees > 0 else 0
        
        # Utilisation des véhicules
        vehicules_utilises = tournees.values('vehicule').distinct().count()
        vehicules_totaux = Vehicule.objects.filter(disponible=True).count()
        taux_utilisation_vehicules = (vehicules_utilises / vehicules_totaux * 100) if vehicules_totaux > 0 else 0
        
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
                'taux_utilisation_vehicules': round(taux_utilisation_vehicules, 1)
            },
            'repartition_statuts': repartition_statuts,
            'performance_transporteurs': transporteurs_stats,
            'total_distance_planifiee': round(sum([float(t.distance_totale or 0) for t in tournees]), 1),
            'economies_estimees': {
                'distance': round(sum([float(t.distance_totale or 0) for t in tournees]) * 0.15, 1),  # 15% d'économie estimée
                'temps': round(nb_tournees * 2.5, 1),  # 2.5h économisées par tournée optimisée
                'cout': round(nb_tournees * 120, 2)  # 120€ économisés par tournée
            }
        }