// frontend/src/pages/planificateur/Dashboard.jsx
// ================================
import React from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  TruckIcon,
  MapIcon,
  ClipboardDocumentListIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

import { dashboardService } from '../../services/api';
import StatCard from '../../components/common/StatCard';
import Loading from '../../components/common/Loading';

const PlanificateurDashboard = () => {
  const { data: dashboardData, isLoading } = useQuery(
    'planificateur-dashboard',
    dashboardService.getPlanificateurDashboard,
    { refetchInterval: 30000 }
  );

  if (isLoading) return <Loading />;

  const { statistiques } = dashboardData;

  return (
    <motion.div 
      className="p-6 space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Planification des transports
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Optimisez les itinéraires et gérez les assignations
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Commandes à assigner"
          value={statistiques.commandes_a_assigner}
          icon={ClipboardDocumentListIcon}
          color="yellow"
        />
        <StatCard
          title="Transporteurs disponibles"
          value={statistiques.transporteurs_disponibles}
          icon={TruckIcon}
          color="green"
        />
        <StatCard
          title="Assignations aujourd'hui"
          value={statistiques.assignations_aujourdhui}
          icon={ChartBarIcon}
          color="blue"
        />
      </div>

      {/* Actions principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link
          to="/planificateur/assignment"
          className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mb-4">
            <TruckIcon className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Assignation automatique
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Assigner automatiquement les transporteurs aux commandes
          </p>
        </Link>

        <Link
          to="/planificateur/optimization"
          className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mb-4">
            <MapIcon className="w-6 h-6 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Optimisation d'itinéraires
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Optimiser les trajets pour réduire les coûts et délais
          </p>
        </Link>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mb-4">
            <ChartBarIcon className="w-6 h-6 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Rapports de performance
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Analyser les performances de la flotte
          </p>
        </div>
      </div>

      {/* Commandes en attente */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Commandes en attente d'assignation
        </h3>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Commande
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Itinéraire
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Poids
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Priorité
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Date
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {/* Placeholder pour les commandes */}
              <tr>
                <td colSpan="5" className="px-6 py-4 text-center text-gray-500">
                  Chargement des commandes...
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
};

export default PlanificateurDashboard;
