// frontend/src/pages/planificateur/OptimizationPanel.jsx
// ================================
import React, { useState } from 'react';
import { useMutation } from 'react-query';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  MapIcon,
  ChartBarIcon,
  PlayIcon,
} from '@heroicons/react/24/outline';

import { planificationService } from '../../services/api';

const OptimizationPanel = () => {
  const [optimizationParams, setOptimizationParams] = useState({
    algorithme: 'tsp',
    critere: 'distance',
    includeTraffic: true,
  });

  const optimizeMutation = useMutation(
    planificationService.optimiserItineraires,
    {
      onSuccess: (data) => {
        toast.success(`${data.resultats.length} itinéraires optimisés`);
      },
      onError: () => {
        toast.error('Erreur lors de l\'optimisation');
      }
    }
  );

  const handleOptimize = () => {
    optimizeMutation.mutate(optimizationParams);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Optimisation des itinéraires
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Optimisez les trajets pour améliorer l'efficacité
        </p>
      </div>

      {/* Paramètres d'optimisation */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Paramètres d'optimisation
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Algorithme
            </label>
            <select
              value={optimizationParams.algorithme}
              onChange={(e) => setOptimizationParams(prev => ({
                ...prev,
                algorithme: e.target.value
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            >
              <option value="tsp">TSP (Travelling Salesman)</option>
              <option value="vrp">VRP (Vehicle Routing)</option>
              <option value="genetic">Algorithme génétique</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Critère d'optimisation
            </label>
            <select
              value={optimizationParams.critere}
              onChange={(e) => setOptimizationParams(prev => ({
                ...prev,
                critere: e.target.value
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            >
              <option value="distance">Distance minimale</option>
              <option value="temps">Temps minimal</option>
              <option value="cout">Coût minimal</option>
              <option value="equilibre">Équilibré</option>
            </select>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="includeTraffic"
              checked={optimizationParams.includeTraffic}
              onChange={(e) => setOptimizationParams(prev => ({
                ...prev,
                includeTraffic: e.target.checked
              }))}
              className="mr-2"
            />
            <label htmlFor="includeTraffic" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Inclure les données de trafic
            </label>
          </div>
        </div>

        <div className="mt-6">
          <button
            onClick={handleOptimize}
            disabled={optimizeMutation.isLoading}
            className="flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {optimizeMutation.isLoading ? (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            ) : (
              <PlayIcon className="w-5 h-5 mr-2" />
            )}
            Lancer l'optimisation
          </button>
        </div>
      </div>

      {/* Résultats */}
      {optimizeMutation.data && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6"
        >
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Résultats de l'optimisation
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {optimizeMutation.data.resultats.length}
              </div>
              <div className="text-sm text-gray-600">Itinéraires optimisés</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
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
