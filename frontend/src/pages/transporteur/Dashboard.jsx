// frontend/src/pages/transporteur/Dashboard.jsx
// ================================
import React from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  TruckIcon,
  MapPinIcon,
  ClockIcon,
  CheckCircleIcon,
  StarIcon,
} from '@heroicons/react/24/outline';

import { dashboardService } from '../../services/api';
import StatCard from '../../components/common/StatCard';
import Loading from '../../components/common/Loading';

const TransporteurDashboard = () => {
  const { data: dashboardData, isLoading } = useQuery(
    'transporteur-dashboard',
    dashboardService.getTransporteurDashboard,
    { refetchInterval: 30000 }
  );

  if (isLoading) return <Loading />;

  const { utilisateur, transporteur, statistiques, missions_recentes } = dashboardData;

  return (
    <motion.div 
      className="p-6 space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Bonjour, {utilisateur.prenom} 🚚
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Voici vos missions du jour
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            transporteur.disponibilite 
              ? 'bg-green-100 text-green-800' 
              : 'bg-red-100 text-red-800'
          }`}>
            {transporteur.disponibilite ? 'Disponible' : 'Indisponible'}
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Missions actives"
          value={statistiques.missions_actives}
          icon={TruckIcon}
          color="blue"
        />
        <StatCard
          title="Missions terminées"
          value={statistiques.missions_terminees}
          icon={CheckCircleIcon}
          color="green"
        />
        <StatCard
          title="Note moyenne"
          value={`${transporteur.rating}/5`}
          icon={StarIcon}
          color="yellow"
        />
        <StatCard
          title="Ce mois"
          value={statistiques.missions_ce_mois}
          icon={ClockIcon}
          color="purple"
        />
      </div>

      {/* Actions rapides */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          to="/transporteur/missions"
          className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mb-4">
            <TruckIcon className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Mes missions
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Voir toutes vos missions
          </p>
        </Link>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mb-4">
            <MapPinIcon className="w-6 h-6 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Navigation
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            GPS intégré pour vos livraisons
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mb-4">
            <ClockIcon className="w-6 h-6 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Historique
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Consulter vos performances
          </p>
        </div>
      </div>

      {/* Missions récentes */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Missions récentes
          </h3>
          <Link
            to="/transporteur/missions"
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            Voir tout
          </Link>
        </div>

        <div className="space-y-4">
          {missions_recentes?.map((mission) => (
            <div
              key={mission.id}
              className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
            >
              <div className="flex-1">
                <div className="font-medium text-gray-900 dark:text-white">
                  #{mission.numero}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {mission.adresse_enlevement?.ville} → {mission.adresse_livraison?.ville}
                </div>
              </div>
              <div className="text-right">
                <div className={`text-sm font-medium ${
                  mission.statut === 'livree' ? 'text-green-600' : 'text-blue-600'
                }`}>
                  {mission.statut_display}
                </div>
                <div className="text-xs text-gray-500">
                  {new Date(mission.date_creation).toLocaleDateString('fr-FR')}
                </div>
              </div>
            </div>
          ))}
        </div>

        {!missions_recentes?.length && (
          <div className="text-center py-8 text-gray-500">
            Aucune mission récente
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default TransporteurDashboard;