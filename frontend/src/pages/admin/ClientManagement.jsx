// frontend/src/pages/admin/ClientManagement.jsx
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
  UserIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';

import { clientService } from '../../services/api';
import Loading from '../../components/common/Loading';
import Modal from '../../components/common/Modal';

const ClientManagement = () => {
  const [selectedClient, setSelectedClient] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { data: clients, isLoading } = useQuery(
    'admin-clients',
    () => clientService.getAll()
  );

  if (isLoading) return <Loading />;

  const clientsList = clients || [];

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Gestion des clients
        </h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <PlusIcon className="w-5 h-5 mr-2" />
          Nouveau client
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <div className="text-2xl font-bold text-blue-600">
            {clientsList.length}
          </div>
          <div className="text-sm text-gray-600">Total clients</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <div className="text-2xl font-bold text-green-600">
            {clientsList.filter(c => c.nb_commandes > 0).length}
          </div>
          <div className="text-sm text-gray-600">Clients actifs</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <div className="text-2xl font-bold text-purple-600">
            {clientsList.filter(c => c.entreprise).length}
          </div>
          <div className="text-sm text-gray-600">Entreprises</div>
        </div>
      </div>

      {/* Table des clients */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Client
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Entreprise
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Commandes
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Note
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Date inscription
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {clientsList.map((client) => (
                <motion.tr
                  key={client.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                          <UserIcon className="h-5 w-5 text-gray-600" />
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {client.utilisateur.full_name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {client.utilisateur.email}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {client.entreprise || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {client.nb_commandes || 0}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {client.rating}/5 ⭐
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(client.utilisateur.user.date_joined).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setSelectedClient(client)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </button>
                      <button className="text-yellow-600 hover:text-yellow-900">
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button className="text-red-600 hover:text-red-900">
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {clientsList.length === 0 && (
          <div className="text-center py-12">
            <UserIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
              Aucun client
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Commencez par ajouter votre premier client.
            </p>
            <div className="mt-6">
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <PlusIcon className="w-5 h-5 mr-2" />
                Ajouter un client
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal détails client */}
      {selectedClient && (
        <Modal
          isOpen={!!selectedClient}
          onClose={() => setSelectedClient(null)}
          title={`Client: ${selectedClient.utilisateur.full_name}`}
          size="lg"
        >
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                  Informations personnelles
                </h4>
                <div className="space-y-2 text-sm">
                  <p><strong>Nom:</strong> {selectedClient.utilisateur.full_name}</p>
                  <p><strong>Email:</strong> {selectedClient.utilisateur.email}</p>
                  <p><strong>Téléphone:</strong> {selectedClient.utilisateur.telephone}</p>
                  {selectedClient.entreprise && (
                    <>
                      <p><strong>Entreprise:</strong> {selectedClient.entreprise}</p>
                      <p><strong>SIRET:</strong> {selectedClient.siret}</p>
                    </>
                  )}
                </div>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                  Statistiques
                </h4>
                <div className="space-y-2 text-sm">
                  <p><strong>Commandes:</strong> {selectedClient.nb_commandes || 0}</p>
                  <p><strong>Note:</strong> {selectedClient.rating}/5</p>
                  <p><strong>Limite crédit:</strong> {selectedClient.credit_limit}€</p>
                  <p><strong>Inscription:</strong> {new Date(selectedClient.utilisateur.user.date_joined).toLocaleDateString('fr-FR')}</p>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setSelectedClient(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Fermer
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default ClientManagement;
