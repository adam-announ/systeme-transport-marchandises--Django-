// frontend/src/pages/client/CommandeList.jsx
// ================================
import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  EyeIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';

import { commandeService } from '../../services/commandes';
import Loading from '../../components/common/Loading';

const CommandeList = () => {
  const [filters, setFilters] = useState({
    search: '',
    statut: '',
    page: 1,
  });

  const { data, isLoading, error } = useQuery(
    ['commandes', filters],
    () => commandeService.getAll(filters),
    { keepPreviousData: true }
  );

  if (isLoading) return <Loading />;
  if (error) return <div className="text-red-600">Erreur de chargement</div>;

  const commandes = data?.results || [];

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

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Mes Commandes
        </h1>
        <Link
          to="/client/commandes/new"
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <PlusIcon className="w-5 h-5 mr-2" />
          Nouvelle commande
        </Link>
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
          </select>
        </div>
      </div>

      {/* Liste des commandes */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Numéro
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Itinéraire
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Marchandise
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
