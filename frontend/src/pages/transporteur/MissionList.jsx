// frontend/src/pages/transporteur/MissionList.jsx
// ================================
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  CheckIcon,
  XMarkIcon,
  MapPinIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

import { commandeService } from '../../services/commandes';
import { transporteurService } from '../../services/transporteurs';
import Loading from '../../components/common/Loading';

const MissionList = () => {
  const [filter, setFilter] = useState('active');
  const queryClient = useQueryClient();

  const { data: missions, isLoading } = useQuery(
    ['transporteur-missions', filter],
    () => commandeService.getAll({ 
      statut: filter === 'active' ? 'assignee,en_transit' : 'livree,annulee' 
    })
  );

  const acceptMutation = useMutation(
    ({ missionId }) => commandeService.changeStatus(missionId, 'acceptee'),
    {
      onSuccess: () => {
        toast.success('Mission acceptée');
        queryClient.invalidateQueries(['transporteur-missions']);
      },
      onError: () => toast.error('Erreur lors de l\'acceptation')
    }
  );

  const refuseMutation = useMutation(
    ({ missionId }) => commandeService.changeStatus(missionId, 'annulee'),
    {
      onSuccess: () => {
        toast.success('Mission refusée');
        queryClient.invalidateQueries(['transporteur-missions']);
      },
      onError: () => toast.error('Erreur lors du refus')
    }
  );

  if (isLoading) return <Loading />;

  const missionsList = missions?.results || [];

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Mes missions
        </h1>
        
        <div className="flex space-x-2">
          <button
            onClick={() => setFilter('active')}
            className={`px-4 py-2 rounded-lg ${
              filter === 'active'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Actives
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={`px-4 py-2 rounded-lg ${
              filter === 'completed'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Terminées
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {missionsList.map((mission) => (
          <motion.div
            key={mission.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6"
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-3">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Commande #{mission.numero}
                  </h3>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    mission.statut === 'assignee' ? 'bg-yellow-100 text-yellow-800' :
                    mission.statut === 'en_transit' ? 'bg-blue-100 text-blue-800' :
                    mission.statut === 'livree' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {mission.statut_display}
                  </span>
                </div>

                <div className