// frontend/src/pages/planificateur/AssignmentPanel.jsx
// ================================
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  PlayIcon,
  UserGroupIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';

import { commandeService } from '../../services/commandes';
import { transporteurService } from '../../services/transporteurs';
import { planificationService } from '../../services/api';
import Loading from '../../components/common/Loading';

const AssignmentPanel = () => {
  const [selectedCommandes, setSelectedCommandes] = useState([]);
  const queryClient = useQueryClient();

  const { data: commandes, isLoading: loadingCommandes } = useQuery(
    'commandes-en-attente',
    () => commandeService.getAll({ statut: 'en_attente' })
  );

  const { data: transporteurs } = useQuery(
    'transporteurs-disponibles',
    () => transporteurService.getAvailable()
  );

  const assignMutation = useMutation(
    planificationService.assignationAutomatique,
    {
      onSuccess: (data) => {
        toast.success(`${data.assignations.length} commandes assignées`);
        queryClient.invalidateQueries(['commandes-en-attente']);
        setSelectedCommandes([]);
      },
      onError: () => {
        toast.error('Erreur lors de l\'assignation');
      }
    }
  );

  const handleSelectCommande = (commandeId) => {
    setSelectedCommandes(prev => 
      prev.includes(commandeId)
        ? prev.filter(id => id !== commandeId)
        : [...prev, commandeId]
    );
  };

  const handleAssignSelected = () => {
    assignMutation.mutate({ commandes: selectedCommandes });
  };

  const handleAssignAll = () => {
    assignMutation.mutate({});
  };

  if (loadingCommandes) return <Loading />;

  const commandesList = commandes?.results || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Assignation des transporteurs
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Gérez l'assignation automatique et manuelle des commandes
          </p>
        </div>

        <div className="flex space-x-3">
          <button
            onClick={handleAssignSelected}
            disabled={selectedCommandes.length === 0 || assignMutation.isLoading}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <CheckIcon className="w-5 h-5 mr-2" />
            Assigner sélectionnées ({selectedCommandes.length})
          </button>
          
          <button
            onClick={handleAssignAll}
            disabled={assignMutation.isLoading}
            className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {assignMutation.isLoading ? (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            ) : (
              <PlayIcon className="w-5 h-5 mr-2" />
            )}
            Assignation automatique
          </button>
        </div>
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <div className="text-2xl font-bold text-blue-600">
                {commandesList.length}
              </div>
              <div className="text-sm text-gray-600">Commandes en attente</div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <div className="text-2xl font-bold text-green-600="font-medium text-gray-900 dark:text-white">
                      #{commande.numero}
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
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {commande.type_marchandise}
                      </div>
                      <div className="text-sm text-gray-500">
                        {commande.poids} kg
                      </div>
                    </div>
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
                    <Link
                      to={`/client/commandes/${commande.id}/track`}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      <EyeIcon className="h-5 w-5" />
                    </Link>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {commandes.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-500 mb-4">Aucune commande trouvée</div>
            <Link
              to="/client/commandes/new"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <PlusIcon className="w-5 h-5 mr-2" />
              Créer votre première commande
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default CommandeList;