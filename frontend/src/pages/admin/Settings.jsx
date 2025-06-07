// frontend/src/pages/admin/Settings.jsx
// ================================
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  CogIcon,
  BellIcon,
  MapIcon,
  CurrencyEuroIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

import { parametresService } from '../../services/api';
import Loading from '../../components/common/Loading';

const Settings = () => {
  const [activeTab, setActiveTab] = useState('general');
  const queryClient = useQueryClient();

  const { data: parametres, isLoading } = useQuery(
    'parametres',
    parametresService.getAll
  );

  const updateMutation = useMutation(
    ({ nom, valeur }) => parametresService.update(nom, valeur),
    {
      onSuccess: () => {
        toast.success('Paramètre mis à jour');
        queryClient.invalidateQueries(['parametres']);
      },
      onError: () => toast.error('Erreur lors de la mise à jour')
    }
  );

  if (isLoading) return <Loading />;

  const tabs = [
    { id: 'general', name: 'Général', icon: CogIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
    { id: 'cartes', name: 'Cartes & GPS', icon: MapIcon },
    { id: 'tarifs', name: 'Tarifs', icon: CurrencyEuroIcon },
    { id: 'securite', name: 'Sécurité', icon: ShieldCheckIcon },
  ];

  const handleUpdateParam = (nom, valeur) => {
    updateMutation.mutate({ nom, valeur });
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Paramètres système
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Configurez les paramètres de l'application
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Navigation */}
        <div className="lg:w-64">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg ${
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'
                      : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-700'
                  }`}
                >
                  <Icon className="mr-3 h-5 w-5" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Contenu */}
        <div className="flex-1">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
            {activeTab === 'general' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Paramètres généraux
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Nom de l'application
                    </label>
                    <input
                      type="text"
                      defaultValue="TransportPro"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('app_name', e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Langue par défaut
                    </label>
                    <select
                      defaultValue="fr"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('default_language', e.target.value)}
                    >
                      <option value="fr">Français</option>
                      <option value="en">English</option>
                      <option value="ar">العربية</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Fuseau horaire
                    </label>
                    <select
                      defaultValue="Africa/Casablanca"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('timezone', e.target.value)}
                    >
                      <option value="Africa/Casablanca">Casablanca (GMT+1)</option>
                      <option value="Europe/Paris">Paris (GMT+1)</option>
                      <option value="UTC">UTC (GMT+0)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Devise
                    </label>
                    <select
                      defaultValue="EUR"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('currency', e.target.value)}
                    >
                      <option value="EUR">Euro (€)</option>
                      <option value="MAD">Dirham marocain (DH)</option>
                      <option value="USD">Dollar US ($)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Paramètres de notification
                </h3>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Notifications email</div>
                      <div className="text-sm text-gray-500">Envoyer des notifications par email</div>
                    </div>
                    <input
                      type="checkbox"
                      defaultChecked={true}
                      className="h-4 w-4 text-blue-600 rounded"
                      onChange={(e) => handleUpdateParam('email_notifications', e.target.checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Notifications SMS</div>
                      <div className="text-sm text-gray-500">Envoyer des notifications par SMS</div>
                    </div>
                    <input
                      type="checkbox"
                      defaultChecked={false}
                      className="h-4 w-4 text-blue-600 rounded"
                      onChange={(e) => handleUpdateParam('sms_notifications', e.target.checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Notifications push</div>
                      <div className="text-sm text-gray-500">Notifications dans le navigateur</div>
                    </div>
                    <input
                      type="checkbox"
                      defaultChecked={true}
                      className="h-4 w-4 text-blue-600 rounded"
                      onChange={(e) => handleUpdateParam('push_notifications', e.target.checked)}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'cartes' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Configuration cartes et GPS
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Clé API Google Maps
                    </label>
                    <input
                      type="password"
                      placeholder="AIzaSy..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('google_maps_api_key', e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Centre de carte par défaut
                    </label>
                    <select
                      defaultValue="casablanca"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('default_map_center', e.target.value)}
                    >
                      <option value="casablanca">Casablanca</option>
                      <option value="rabat">Rabat</option>
                      <option value="marrakech">Marrakech</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'tarifs' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Configuration des tarifs
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Tarif de base (€)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      defaultValue="50.00"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('base_rate', e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Tarif par kg (€)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      defaultValue="2.00"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('weight_rate', e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Tarif par km (€)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      defaultValue="1.50"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('distance_rate', e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Majoration urgente (%)
                    </label>
                    <input
                      type="number"
                      step="1"
                      defaultValue="50"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('urgent_surcharge', e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'securite' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Paramètres de sécurité
                </h3>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Authentification à deux facteurs</div>
                      <div className="text-sm text-gray-500">Obligatoire pour les administrateurs</div>
                    </div>
                    <input
                      type="checkbox"
                      defaultChecked={true}
                      className="h-4 w-4 text-blue-600 rounded"
                      onChange={(e) => handleUpdateParam('require_2fa', e.target.checked)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Durée de session (minutes)
                    </label>
                    <input
                      type="number"
                      defaultValue="60"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('session_timeout', e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Tentatives de connexion max
                    </label>
                    <input
                      type="number"
                      defaultValue="5"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                      onChange={(e) => handleUpdateParam('max_login// ================================
