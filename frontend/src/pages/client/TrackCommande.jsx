// frontend/src/pages/client/TrackCommande.jsx
// ================================
import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import { motion } from 'framer-motion';
import {
  MapPinIcon,
  ClockIcon,
  TruckIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

import { commandeService } from '../../services/commandes';
import Loading from '../../components/common/Loading';
import GoogleMap from '../../components/maps/GoogleMap';

const TrackCommande = () => {
  const { id } = useParams();

  const { data: commande, isLoading } = useQuery(
    ['commande', id],
    () => commandeService.getById(id),
    { refetchInterval: 30000 }
  );

  const { data: tracking } = useQuery(
    ['tracking', id],
    () => commandeService.getTracking(id),
    { refetchInterval: 10000 }
  );

  if (isLoading) return <Loading />;
  if (!commande) return <div>Commande non trouvée</div>;

  const steps = [
    { key: 'commande_creee', label: 'Commande créée', icon: CheckCircleIcon },
    { key: 'transporteur_assigne', label: 'Transporteur assigné', icon: TruckIcon },
    { key: 'en_transit', label: 'En transit', icon: TruckIcon },
    { key: 'livree', label: 'Livrée', icon: CheckCircleIcon },
  ];

  const getCurrentStep = () => {
    const statusMap = {
      'en_attente': 0,
      'assignee': 1,
      'en_transit': 2,
      'livree': 3,
    };
    return statusMap[commande.statut] || 0;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Suivi de la commande #{commande.numero}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {commande.adresse_enlevement?.ville} → {commande.adresse_livraison?.ville}
          </p>
        </div>
      </div>

      {/* Étapes de suivi */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold mb-6">État de la livraison</h3>
        
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const isActive = index <= getCurrentStep();
            const isCompleted = index < getCurrentStep();
            
            return (
              <div key={step.key} className="flex flex-col items-center flex-1">
                <div className={`
                  flex items-center justify-center w-12 h-12 rounded-full border-2
                  ${isActive 
                    ? 'border-blue-600 bg-blue-600 text-white' 
                    : 'border-gray-300 bg-white text-gray-400'
                  }
                `}>
                  <step.icon className="w-6 h-6" />
                </div>
                
                <div className="mt-2 text-center">
                  <div className={`text-sm font-medium ${isActive ? 'text-blue-600' : 'text-gray-500'}`}>
                    {step.label}
                  </div>
                </div>
                
                {index < steps.length - 1 && (
                  <div className={`
                    hidden sm:block w-full h-0.5 mt-6
                    ${isCompleted ? 'bg-blue-600' : 'bg-gray-300'}
                  `} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Informations de la commande */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">Détails de la commande</h3>
          
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Type de marchandise:</span>
              <span className="font-medium">{commande.type_marchandise}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Poids:</span>
              <span className="font-medium">{commande.poids} kg</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Priorité:</span>
              <span className="font-medium">{commande.priorite_display}</span>
            </div>
            {commande.transporteur_nom && (
              <div className="flex justify-between">
                <span className="text-gray-600">Transporteur:</span>
                <span className="font-medium">{commande.transporteur_nom}</span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">Historique</h3>
          
          <div className="space-y-3">
            {tracking?.map((event, index) => (
              <div key={index} className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-2 h-2 bg-blue-600 rounded-full mt-2"></div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {event.description}
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(event.timestamp).toLocaleString('fr-FR')}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Carte si transporteur assigné */}
      {commande.transporteur && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">Localisation en temps réel</h3>
          <div className="h-96">
            <GoogleMap
              pickup={commande.adresse_enlevement}
              delivery={commande.adresse_livraison}
              height="100%"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default TrackCommande;
