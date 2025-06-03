import React from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { 
  PlusIcon, 
  TruckIcon, 
  EyeIcon, 
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';
import { motion } from 'framer-motion';

import { dashboardService } from '../../services/api';
import StatCard from '../../components/common/StatCard';
import Loading from '../../components/common/Loading';
import CommandeTable from '../../components/tables/CommandeTable';
import DashboardChart from '../../components/charts/DashboardChart';

const ClientDashboard = () => {
  const { data: dashboardData, isLoading, error } = useQuery(
    'client-dashboard',
    dashboardService.getClientDashboard,
    {
      refetchInterval: 30000, // Actualisation toutes les 30 secondes
    }
  );

  if (isLoading) return <Loading />;
  if (error) return <div className="p-6 text-center text-red-600">Erreur lors du chargement</div>;

  const { utilisateur, statistiques, commandes_recentes, notifications_non_lues } = dashboardData;

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 100
      }
    }
  };

  return (
    <motion.div 
      className="p-6 space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div 
        className="flex justify-between items-center"
        variants={itemVariants}
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Bonjour, {utilisateur.prenom} 👋
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Voici un aperçu de vos expéditions
          </p>
        </div>
        
        <Link
          to="/client/commandes/new"
          className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200 shadow-sm hover:shadow-md"
        >
          <PlusIcon className="w-5 h-5 mr-2" />
          Nouvelle commande
        </Link>
      </motion.div>

      {/* Notifications */}
      {notifications_non_lues.length > 0 && (
        <motion.div 
          className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4"
          variants={itemVariants}
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Vous avez {notifications_non_lues.length} nouvelle(s) notification(s)
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Stats Cards */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        variants={itemVariants}
      >
        <StatCard
          title="Total Commandes"
          value={statistiques.total_commandes}
          icon={TruckIcon}
          color="blue"
          trend="+12% ce mois"
        />
        <StatCard
          title="En cours"
          value={statistiques.commandes_en_cours}
          icon={ClockIcon}
          color="yellow"
          trend={`${statistiques.commandes_en_cours} actives`}
        />
        <StatCard
          title="Livrées"
          value={statistiques.commandes_livrees}
          icon={CheckCircleIcon}
          color="green"
          trend="98% de réussite"
        />
        <StatCard
          title="Montant total"
          value={`${statistiques.montant_total?.toLocaleString('fr-FR')} €`}
          icon={ChartBarIcon}
          color="purple"
          trend="+8% ce mois"
        />
      </motion.div>

      {/* Actions rapides */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
        variants={itemVariants}
      >
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow duration-200">
          <div className="flex items-center justify-center w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-lg mb-4">
            <PlusIcon className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Nouvelle commande
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Créer une nouvelle demande de transport
          </p>
          <Link
            to="/client/commandes/new"
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            Créer →
          </Link>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow duration-200">
          <div className="flex items-center justify-center w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-lg mb-4">
            <EyeIcon className="w-6 h-6 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Suivre une commande
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Suivre l'état de vos commandes en temps réel
          </p>
          <Link
            to="/client/commandes"
            className="text-green-600 hover:text-green-700 font-medium"
          >
            Suivre →
          </Link>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow duration-200">
          <div className="flex items-center justify-center w-12 h-12 bg-purple-100 dark:bg-purple-900/20 rounded-lg mb-4">
            <ChartBarIcon className="w-6 h-6 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Rapports
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Consulter vos statistiques et rapports
          </p>
          <button className="text-purple-600 hover:text-purple-700 font-medium">
            Consulter →
          </button>
        </div>
      </motion.div>

      {/* Chart et commandes récentes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Graphique */}
        <motion.div 
          className="lg:col-span-2"
          variants={itemVariants}
        >
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Évolution des commandes
            </h3>
            <DashboardChart data={statistiques} />
          </div>
        </motion.div>

        {/* Commandes récentes */}
        <motion.div variants={itemVariants}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Commandes récentes
              </h3>
              <Link
                to="/client/commandes"
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Voir tout
              </Link>
            </div>

            <div className="space-y-3">
              {commandes_recentes.map((commande) => (
                <div
                  key={commande.id}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 dark:text-white">
                      #{commande.numero}
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {commande.adresse_enlevement.ville} → {commande.adresse_livraison.ville}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusStyle(commande.statut)}`}>
                      {commande.statut_display}
                    </span>
                    <Link
                      to={`/client/commandes/${commande.id}/track`}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      <EyeIcon className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>

            {commandes_recentes.length === 0 && (
              <div className="text-center py-8">
                <TruckIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
                  Aucune commande
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Créez votre première commande pour commencer.
                </p>
                <div className="mt-6">
                  <Link
                    to="/client/commandes/new"
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
                  >
                    <PlusIcon className="w-4 h-4 mr-2" />
                    Nouvelle commande
                  </Link>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};

// Fonction utilitaire pour les styles de statut
function getStatusStyle(statut) {
  const styles = {
    'en_attente': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
    'assignee': 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
    'en_transit': 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
    'livree': 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
    'annulee': 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
  };
  
  return styles[statut] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
}

export default ClientDashboard;