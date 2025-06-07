// frontend/src/pages/admin/CommandeManagement.jsx
// ================================
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  EyeIcon,
  PencilIcon,
  TrashIcon,
  UserIcon,
  CheckIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

import { commandeService } from '../../services/commandes';
import { transporteurService } from '../../services/transporteurs';
import Loading from '../../components/common/Loading';
import Modal from '../../components/common/Modal';

const CommandeManagement = () => {
  const [filters, setFilters] = useState({
    search: '',
    statut: '',
    page: 1,
  });
  const [selectedCommande, setSelectedCommande] = useState(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const queryClient = useQueryClient();

  const { data: commandesData, isLoading } = useQuery(
    ['admin-commandes', filters],
    () => commandeService.getAll(filters),
    { keepPreviousData: true }
  );

  const { data: transporteurs } = useQuery(
    'transporteurs-all',
    () => transporteurService.getAll()
  );

  const assignMutation = useMutation(
    commandeService.assignTransporteur,
    {
      onSuccess: () => {
        toast.success('Transporteur assigné avec succès');
        queryClient.invalidateQueries(['admin-commandes']);
        setShowAssignModal(false);
        setSelectedCommande(null);
      },
      onError: () => toast.error('Erreur lors de l\'assignation')
    }
  );

  const statusMutation = useMutation(
    ({ commandeId, status }) => commandeService.changeStatus(commandeId, status),
    {
      onSuccess: () => {
        toast.success('Statut mis à jour');
        queryClient.invalidateQueries(['admin-commandes']);
      },
      onError: () => toast.error('Erreur lors de la mise à jour')
    }
  );

  if (isLoading) return <Loading />;

  const commandes = commandesData?.results || [];

  const getStatusStyle = (statut) => {
    const styles = {
      'en_attente': 'bg-yellow-100 text-yellow-800',
      'assignee': 'bg-blue-100 text-blue-800',
      'en_transit': 'bg-purple-100 text-purple-800',
      'livree': 'bg-green-100 text-green-800',
      'annulee': 'bg-red-100 text-red-800',
    };
    return styles[statut] || 'bg-gray-100 text-gray-800';
  };

  const handleAssignTransporteur = (commande) => {
    setSelectedCommande(commande);
    setShowAssignModal(true);
  };

  const handleAssign = (transporteurId) => {
    if (selectedCommande && transporteurId) {
      assignMutation.mutate({
        commandeId: selectedCommande.id,
        transporteurId
      });
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Gestion des commandes
        </h1>
      </div>

      {/* Filtres */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
          
          <select
            value={filters.statut}
            onChange={(e) => setFilters(prev => ({ ...prev, statut: e.target.value }))}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
          >
            <option value="">Tous les statuts</option>
            <option value="en_attente">En attente</option>
            <option value="assignee">Assignée</option>
            <option value="en_transit">En transit</option>
            <option value="livree">Livrée</option>
            <option value="annulee">Annulée</option>
          </select>
        </div>
      </div>

      {/* Table des commandes */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Commande
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Client
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Itinéraire
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Transporteur
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {commandes.map((commande) => (
                <motion.tr
                  key={commande.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium text-gray-900 dark:text-white">
                      #{commande.numero}
                    </div>
                    <div className="text-sm text-gray-500">
                      {commande.type_marchandise} - {commande.poids} kg
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {commande.client_nom}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      <div>{commande.adresse_enlevement?.ville}</div>
                      <div className="text-xs text-gray-500">↓</div>
                      <div>{commande.adresse_livraison?.ville}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {commande.transporteur_nom ? (
                      <div className="text-sm text-gray-900 dark:text-white">
                        {commande.transporteur_nom}
                      </div>
                    ) : (
                      <button
                        onClick={() => handleAssignTransporteur(commande)}
                        className="text-blue-600 hover:text-blue-900 text-sm font-medium"
                      >
                        Assigner
                      </button>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusStyle(commande.statut)}`}>
                      {commande.statut_display}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(commande.date_creation).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <Link
                        to={`/admin/commandes/${commande.id}`}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </Link>
                      
                      {commande.statut === 'en_attente' && (
                        <button
                          onClick={() => statusMutation.mutate({ 
                            commandeId: commande.id, 
                            status: 'assignee' 
                          })}
                          className="text-green-600 hover:text-green-900"
                        >
                          <CheckIcon className="h-4 w-4" />
                        </button>
                      )}
                      
                      <button
                        onClick={() => statusMutation.mutate({ 
                          commandeId: commande.id, 
                          status: 'annulee' 
                        })}
                        className="text-red-600 hover:text-red-900"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {commandes.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-500 mb-4">Aucune commande trouvée</div>
          </div>
        )}
      </div>

      {/* Modal d'assignation */}
      <Modal
        isOpen={showAssignModal}
        onClose={() => setShowAssignModal(false)}
        title="Assigner un transporteur"
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            Sélectionnez un transporteur pour la commande #{selectedCommande?.numero}
          </p>
          
          <div className="space-y-2">
            {transporteurs?.filter(t => t.disponibilite).map((transporteur) => (
              <button
                key={transporteur.id}
                onClick={() => handleAssign(transporteur.id)}
                disabled={assignMutation.isLoading}
                className="w-full text-left p-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                <div className="flex justify-between items-center">
                  <div>
                    <div className="font-medium">
                      {transporteur.utilisateur.full_name}
                    </div>
                    <div className="text-sm text-gray-500">
                      {transporteur.type_vehicule} - {transporteur.capacite_charge} kg
                    </div>
                  </div>
                  <div className="text-sm text-green-600">
                    Disponible
                  </div>
                </div>
              </button>
            ))}
          </div>

          {!transporteurs?.filter(t => t.disponibilite).length && (
            <div className="text-center py-4 text-gray-500">
              Aucun transporteur disponible
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default CommandeManagement;">
                {optimizeMutation.data.gain_distance || '0'}%
              </div>
              <div className="text-sm text-gray-600">Réduction distance</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {optimizeMutation.data.gain_temps || '0'}%
              </div>
              <div className="text-sm text-gray-600">Gain de temps</div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead>
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Commande
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Distance
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Durée
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Statut
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {optimizeMutation.data.resultats.map((resultat) => (
                  <tr key={resultat.commande_id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      #{resultat.commande_numero}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {resultat.distance} km
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {resultat.duree} min
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        Optimisé
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default OptimizationPanel;