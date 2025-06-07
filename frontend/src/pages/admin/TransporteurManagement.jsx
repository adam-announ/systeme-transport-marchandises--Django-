// frontend/src/pages/admin/TransporteurManagement.jsx
// ================================
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  EyeIcon,
  PencilIcon,
  TrashIcon,
  PlusIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

import { transporteurService } from '../../services/transporteurs';
import Loading from '../../components/common/Loading';
import Modal from '../../components/common/Modal';

const TransporteurManagement = () => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTransporteur, setSelectedTransporteur] = useState(null);
  const queryClient = useQueryClient();

  const { data: transporteurs, isLoading } = useQuery(
    'admin-transporteurs',
    () => transporteurService.getAll()
  );

  const toggleMutation = useMutation(
    transporteurService.toggleDisponibilite,
    {
      onSuccess: () => {
        toast.success('Disponibilité mise à jour');
        queryClient.invalidateQueries(['admin-transporteurs']);
      },
      onError: () => toast.error('Erreur lors de la mise à jour')
    }
  );

  const deleteMutation = useMutation(
    transporteurService.delete,
    {
      onSuccess: () => {
        toast.success('Transporteur supprimé');
        queryClient.invalidateQueries(['admin-transporteurs']);
      },
      onError: () => toast.error('Erreur lors de la suppression')
    }
  );

  if (isLoading) return <Loading />;

  const transporteursList = transporteurs || [];

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Gestion des transporteurs
        </h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <PlusIcon className="w-5 h-5 mr-2" />
          Nouveau transporteur
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <div className="text-2xl font-bold text-blue-600">
            {transporteursList.length}
          </div>
          <div className="text-sm text-gray-600">Total transporteurs</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <div className="text-2xl font-bold text-green-600">
            {transporteursList.filter(t => t.disponibilite).length}
          </div>
          <div className="text-sm text-gray-600">Disponibles</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <div className="text-2xl font-bold text-purple-600">
            {transporteursList.filter(t => t.nb_missions_actives > 0).length}
          </div>
          <div className="text-sm text-gray-600">En mission</div>
        </div>
      </div>

      {/* Table des transporteurs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Transporteur
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Véhicule
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Capacité
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Missions actives
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Note
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {transporteursList.map((transporteur) => (
                <motion.tr
                  key={transporteur.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {transporteur.utilisateur.full_name}
                      </div>
                      <div className="text-sm text-gray-500">
                        {transporteur.matricule}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {transporteur.type_vehicule}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {transporteur.capacite_charge} kg
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {transporteur.nb_missions_actives || 0}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {transporteur.rating}/5 ⭐
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => toggleMutation.mutate(transporteur.id)}
                      disabled={toggleMutation.isLoading}
                      className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full ${
                        transporteur.disponibilite
                          ? 'bg-green-100 text-green-800 hover:bg-green-200'
                          : 'bg-red-100 text-red-800 hover:bg-red-200'
                      }`}
                    >
                      {transporteur.disponibilite ? (
                        <>
                          <CheckCircleIcon className="w-3 h-3 mr-1" />
                          Disponible
                        </>
                      ) : (
                        <>
                          <XCircleIcon className="w-3 h-3 mr-1" />
                          Indisponible
                        </>
                      )}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setSelectedTransporteur(transporteur)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </button>
                      <button className="text-yellow-600 hover:text-yellow-900">
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => {
                          if (window.confirm('Êtes-vous sûr de vouloir supprimer ce transporteur ?')) {
                            deleteMutation.mutate(transporteur.id);
                          }
                        }}
                        className="text-red-600 hover:text-red-900"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {transporteursList.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-500 mb-4">Aucun transporteur trouvé</div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 // ================================
