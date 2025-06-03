import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  ChartBarIcon,
  TruckIcon,
  UsersIcon,
  ExclamationTriangleIcon,
  CogIcon,
  DocumentArrowDownIcon,
  PlusIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  CheckIcon,
  XMarkIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

import { dashboardService, commandeService, transporteurService, exportService } from '../../services/api';
import StatCard from '../../components/common/StatCard';
import Loading from '../../components/common/Loading';
import Modal from '../../components/common/Modal';
import ConfirmDialog from '../../components/common/ConfirmDialog';
import DashboardChart from '../../components/charts/DashboardChart';

const AdminDashboard = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const [showCommandeModal, setShowCommandeModal] = useState(false);
  const [showTransporteurModal, setShowTransporteurModal] = useState(false);
  const [selectedCommande, setSelectedCommande] = useState(null);
  const [commandeFilters, setCommandeFilters] = useState({
    statut: '',
    transporteur: '',
    search: ''
  });

  const queryClient = useQueryClient();

  // Queries
  const { data: dashboardData, isLoading } = useQuery(
    ['admin-dashboard', selectedPeriod],
    () => dashboardService.getAdminDashboard({ period: selectedPeriod }),
    { refetchInterval: 30000 }
  );

  const { data: commandesData, isLoading: isLoadingCommandes } = useQuery(
    ['commandes', commandeFilters],
    () => commandeService.getAll(commandeFilters),
    { keepPreviousData: true }
  );

  const { data: transporteursData } = useQuery(
    'transporteurs',
    () => transporteurService.getAll()
  );

  // Mutations
  const assignMutation = useMutation(commandeService.assignTransporteur, {
    onSuccess: () => {
      toast.success('Transporteur assigné avec succès');
      queryClient.invalidateQueries(['commandes']);
      queryClient.invalidateQueries(['admin-dashboard']);
    },
    onError: (error) => {
      toast.error(error.message);
    }
  });

  const statusMutation = useMutation(
    ({ commandeId, status, data }) => commandeService.changeStatus(commandeId, status, data),
    {
      onSuccess: () => {
        toast.success('Statut mis à jour');
        queryClient.invalidateQueries(['commandes']);
      },
      onError: (error) => {
        toast.error(error.message);
      }
    }
  );

  if (isLoading) return <Loading />;

  const { statistiques, commandes_recentes, incidents_recents, notifications_non_lues } = dashboardData;

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { type: "spring", stiffness: 100 }
    }
  };

  const handleAssignTransporteur = async (commandeId, transporteurId) => {
    await assignMutation.mutateAsync({ commandeId, transporteurId });
  };

  const handleStatusChange = async (commandeId, status) => {
    await statusMutation.mutateAsync({ commandeId, status });
  };

  const handleExport = async (type) => {
    try {
      await exportService.exportCommandes(type, commandeFilters);
      toast.success(`Export ${type.toUpperCase()} réussi`);
    } catch (error) {
      toast.error('Erreur lors de l\'export');
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
        className="flex flex-col lg:flex-row lg:items-center lg:justify-between"
        variants={itemVariants}
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Administration TransportPro
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Vue d'ensemble du système et gestion des opérations
          </p>
        </div>
        
        <div className="mt-4 lg:mt-0 flex space-x-3">
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
          >
            <option value="day">Aujourd'hui</option>
            <option value="week">Cette semaine</option>
            <option value="month">Ce mois</option>
            <option value="year">Cette année</option>
          </select>
          
          <button
            onClick={() => handleExport('csv')}
            className="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg"
          >
            <DocumentArrowDownIcon className="w-4 h-4 mr-2" />
            Exporter
          </button>
        </div>
      </motion.div>

      {/* Alertes */}
      {incidents_recents.length > 0 && (
        <motion.div 
          className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-4"
          variants={itemVariants}
        >
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                {incidents_recents.length} incident(s) nécessite(nt) votre attention
              </p>
            </div>
            <div className="ml-auto">
              <Link
                to="/admin/incidents"
                className="text-sm text-red-600 hover:text-red-500 font-medium"
              >
                Voir tous →
              </Link>
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
          icon={ChartBarIcon}
          color="blue"
          trend="+12% ce mois"
          onClick={() => setShowCommandeModal(true)}
        />
        <StatCard
          title="En cours"
          value={statistiques.commandes_en_cours}
          icon={ArrowPathIcon}
          color="yellow"
          trend={`${statistiques.commandes_en_cours} actives`}
        />
        <StatCard
          title="Transporteurs"
          value={`${statistiques.transporteurs_disponibles}/${statistiques.total_transporteurs}`}
          icon={TruckIcon}
          color="green"
          trend="Disponibles/Total"
          onClick={() => setShowTransporteurModal(true)}
        />
        <StatCard
          title="Chiffre d'affaires"
          value={`${statistiques.chiffre_affaires_mensuel?.toLocaleString('fr-FR')} €`}
          icon={CurrencyEuroIcon}
          color="purple"
          trend="+15% ce mois"
        />
      </motion.div>

      {/* Actions rapides */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-4 gap-6"
        variants={itemVariants}
      >
        <Link
          to="/admin/commandes"
          className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-all duration-200 group"
        >
          <div className="flex items-center justify-center w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-lg mb-4 group-hover:scale-110 transition-transform">
            <ChartBarIcon className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Gérer Commandes
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            {statistiques.commandes_en_attente} en attente
          </p>
        </Link>

        <Link
          to="/admin/transporteurs"
          className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-all duration-200 group"
        >
          <div className="flex items-center justify-center w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-lg mb-4 group-hover:scale-110 transition-transform">
            <TruckIcon className="w-6 h-6 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Transporteurs
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            {statistiques.transporteurs_disponibles} disponibles
          </p>
        </Link>

        <Link
          to="/admin/clients"
          className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-all duration-200 group"
        >
          <div className="flex items-center justify-center w-12 h-12 bg-purple-100 dark:bg-purple-900/20 rounded-lg mb-4 group-hover:scale-110 transition-transform">
            <UsersIcon className="w-6 h-6 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Clients
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            {statistiques.total_clients} clients
          </p>
        </Link>

        <Link
          to="/admin/settings"
          className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-all duration-200 group"
        >
          <div className="flex items-center justify-center w-12 h-12 bg-orange-100 dark:bg-orange-900/20 rounded-lg mb-4 group-hover:scale-110 transition-transform">
            <CogIcon className="w-6 h-6 text-orange-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Paramètres
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Configuration système
          </p>
        </Link>
      </motion.div>

      {/* Charts et données */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Graphique principal */}
        <motion.div 
          className="lg:col-span-2"
          variants={itemVariants}
        >
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Évolution des commandes
              </h3>
              <div className="flex space-x-2">
                <button className="px-3 py-1 text-xs font-medium bg-blue-100 text-blue-600 rounded-full">
                  Commandes
                </button>
                <button className="px-3 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
                  Revenus
                </button>
              </div>
            </div>
            <DashboardChart 
              data={statistiques} 
              type="commandes"
              height={300}
            />
          </div>
        </motion.div>

        {/* Activité récente */}
        <motion.div variants={itemVariants}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Activité récente
              </h3>
              <Link
                to="/admin/journal"
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Voir tout
              </Link>
            </div>

            <div className="space-y-4">
              {commandes_recentes.slice(0, 5).map((commande) => (
                <div
                  key={commande.id}
                  className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className={`
                    w-2 h-2 rounded-full
                    ${commande.statut === 'en_attente' ? 'bg-yellow-400' :
                      commande.statut === 'en_cours' ? 'bg-blue-400' :
                      commande.statut === 'livree' ? 'bg-green-400' : 'bg-gray-400'}
                  `} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      Commande #{commande.numero}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {commande.client_nom} • {commande.statut_display}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedCommande(commande)}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    <EyeIcon className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Commandes en attente */}
      <motion.div variants={itemVariants}>
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Commandes nécessitant une action
              </h3>
              
              <div className="mt-4 sm:mt-0 flex space-x-3">
                <div className="relative">
                  <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Rechercher..."
                    value={commandeFilters.search}
                    onChange={(e) => setCommandeFilters(prev => ({ ...prev, search: e.target.value }))}
                    className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700"
                  />
                </div>
                
                <select
                  value={commandeFilters.statut}
                  onChange={(e) => setCommandeFilters(prev => ({ ...prev, statut: e.target.value }))}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700"
                >
                  <option value="">Tous les statuts</option>
                  <option value="en_attente">En attente</option>
                  <option value="assignee">Assignée</option>
                  <option value="en_cours">En cours</option>
                  <option value="livree">Livrée</option>
                  <option value="annulee">Annulée</option>
                </select>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Commande
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Client
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Itinéraire
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Transporteur
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Statut
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {isLoadingCommandes ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-4 text-center">
                      <div className="flex justify-center">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                      </div>
                    </td>
                  </tr>
                ) : commandesData?.results?.length > 0 ? (
                  commandesData.results.map((commande) => (
                    <tr key={commande.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            #{commande.numero}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {new Date(commande.date_creation).toLocaleDateString('fr-FR')}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {commande.client_nom}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {commande.type_marchandise} - {commande.poids} kg
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 dark:text-white">
                          <div>{commande.adresse_enlevement?.ville}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">↓</div>
                          <div>{commande.adresse_livraison?.ville}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {commande.transporteur_nom ? (
                          <div className="text-sm">
                            <div className="font-medium text-gray-900 dark:text-white">
                              {commande.transporteur_nom}
                            </div>
                            <div className="text-green-600 text-xs">Assigné</div>
                          </div>
                        ) : (
                          <select
                            onChange={(e) => {
                              if (e.target.value) {
                                handleAssignTransporteur(commande.id, e.target.value);
                              }
                            }}
                            className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700"
                            defaultValue=""
                          >
                            <option value="">Assigner transporteur</option>
                            {transporteursData?.filter(t => t.disponibilite).map(transporteur => (
                              <option key={transporteur.id} value={transporteur.id}>
                                {transporteur.utilisateur.full_name}
                              </option>
                            ))}
                          </select>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusStyle(commande.statut)}`}>
                          {commande.statut_display}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex space-x-2">
                          <button
                            onClick={() => setSelectedCommande(commande)}
                            className="text-blue-600 hover:text-blue-900"
                            title="Voir détails"
                          >
                            <EyeIcon className="h-4 w-4" />
                          </button>
                          
                          {commande.statut === 'en_attente' && (
                            <button
                              onClick={() => handleStatusChange(commande.id, 'assignee')}
                              className="text-green-600 hover:text-green-900"
                              title="Marquer comme assignée"
                            >
                              <CheckIcon className="h-4 w-4" />
                            </button>
                          )}
                          
                          <button
                            onClick={() => handleStatusChange(commande.id, 'annulee')}
                            className="text-red-600 hover:text-red-900"
                            title="Annuler"
                          >
                            <XMarkIcon className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="6" className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                      Aucune commande trouvée
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {commandesData?.count > 10 && (
            <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Affichage de {commandesData.results.length} sur {commandesData.count} commandes
                </div>
                <Link
                  to="/admin/commandes"
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  Voir toutes les commandes →
                </Link>
              </div>
            </div>
          )}
        </div>
      </motion.div>

      {/* Modal détails commande */}
      {selectedCommande && (
        <Modal
          isOpen={!!selectedCommande}
          onClose={() => setSelectedCommande(null)}
          title={`Commande #${selectedCommande.numero}`}
          size="lg"
        >
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                  Informations client
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Nom:</strong> {selectedCommande.client_nom}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Marchandise:</strong> {selectedCommande.type_marchandise}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Poids:</strong> {selectedCommande.poids} kg
                </p>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                  État de la commande
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Statut:</strong> 
                  <span className={`ml-2 px-2 py-1 text-xs rounded-full ${getStatusStyle(selectedCommande.statut)}`}>
                    {selectedCommande.statut_display}
                  </span>
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Transporteur:</strong> {selectedCommande.transporteur_nom || 'Non assigné'}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Prix estimé:</strong> {selectedCommande.prix_estime || 'Non calculé'} €
                </p>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                Itinéraire
              </h4>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="flex items-center space-x-4">
                  <div className="text-sm">
                    <div className="font-medium">Enlèvement</div>
                    <div className="text-gray-600 dark:text-gray-400">
                      {selectedCommande.adresse_enlevement?.rue}, {selectedCommande.adresse_enlevement?.ville}
                    </div>
                  </div>
                  <div className="text-gray-400">→</div>
                  <div className="text-sm">
                    <div className="font-medium">Livraison</div>
                    <div className="text-gray-600 dark:text-gray-400">
                      {selectedCommande.adresse_livraison?.rue}, {selectedCommande.adresse_livraison?.ville}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {selectedCommande.description && (
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                  Description
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedCommande.description}
                </p>
              </div>
            )}

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setSelectedCommande(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Fermer
              </button>
              <Link
                to={`/admin/commandes/${selectedCommande.id}`}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
              >
                Voir détails complets
              </Link>
            </div>
          </div>
        </Modal>
      )}
    </motion.div>
  );
};

// Fonction utilitaire pour les styles de statut
function getStatusStyle(statut) {
  const styles = {
    'en_attente': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
    'assignee': 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
    'en_cours': 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
    'en_transit': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/20 dark:text-indigo-400',
    'livree': 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
    'annulee': 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
  };
  
  return styles[statut] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
}

export default AdminDashboard;