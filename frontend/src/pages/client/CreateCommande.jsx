import React, { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useNavigate } from 'react-router-dom';
import { useMutation } from 'react-query';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  TruckIcon,
  MapPinIcon,
  ScaleIcon,
  CurrencyEuroIcon,
  CalendarIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

import { commandeService } from '../../services/commandes';
import { GoogleMap } from '../../components/maps/GoogleMap';
import AdresseForm from '../../components/forms/AdresseForm';
import Loading from '../../components/common/Loading';

// Schéma de validation
const schema = yup.object({
  type_marchandise: yup.string().required('Type de marchandise requis'),
  description: yup.string(),
  poids: yup.number().positive('Le poids doit être positif').required('Poids requis'),
  volume: yup.number().positive('Le volume doit être positif'),
  valeur_declaree: yup.number().positive('La valeur doit être positive'),
  instructions_speciales: yup.string(),
  adresse_enlevement: yup.object({
    rue: yup.string().required('Rue requise'),
    ville: yup.string().required('Ville requise'),
    code_postal: yup.string().required('Code postal requis'),
    pays: yup.string().required('Pays requis'),
  }).required(),
  adresse_livraison: yup.object({
    rue: yup.string().required('Rue requise'),
    ville: yup.string().required('Ville requise'),
    code_postal: yup.string().required('Code postal requis'),
    pays: yup.string().required('Pays requis'),
  }).required(),
  contact_enlevement: yup.string(),
  contact_livraison: yup.string(),
  telephone_enlevement: yup.string(),
  telephone_livraison: yup.string(),
  date_enlevement_prevue: yup.date(),
  date_livraison_prevue: yup.date(),
  priorite: yup.string().required('Priorité requise'),
});

const TYPES_MARCHANDISE = [
  { value: 'electronique', label: 'Électronique' },
  { value: 'textile', label: 'Textile' },
  { value: 'alimentaire', label: 'Alimentaire' },
  { value: 'mobilier', label: 'Mobilier' },
  { value: 'chimique', label: 'Produits chimiques' },
  { value: 'fragile', label: 'Fragile' },
  { value: 'dangereux', label: 'Matières dangereuses' },
  { value: 'autre', label: 'Autre' },
];

const PRIORITES = [
  { value: 'basse', label: 'Basse', color: 'text-green-600' },
  { value: 'normale', label: 'Normale', color: 'text-blue-600' },
  { value: 'haute', label: 'Haute', color: 'text-orange-600' },
  { value: 'urgente', label: 'Urgente', color: 'text-red-600' },
];

const CreateCommande = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [estimatedCost, setEstimatedCost] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid }
  } = useForm({
    resolver: yupResolver(schema),
    defaultValues: {
      type_marchandise: '',
      poids: '',
      volume: '',
      priorite: 'normale',
      adresse_enlevement: {
        pays: 'Maroc'
      },
      adresse_livraison: {
        pays: 'Maroc'
      }
    },
    mode: 'onChange'
  });

  const createMutation = useMutation(commandeService.create, {
    onSuccess: (data) => {
      toast.success('Commande créée avec succès !');
      navigate(`/client/commandes/${data.id}/track`);
    },
    onError: (error) => {
      toast.error(error.message || 'Erreur lors de la création');
    }
  });

  const watchedValues = watch();

  // Calculer l'estimation de prix
  useEffect(() => {
    const calculateCost = () => {
      const { poids, volume, priorite } = watchedValues;
      
      if (poids && routeInfo?.distance) {
        const baseCost = 50; // Coût de base
        const weightCost = poids * 2; // 2€ par kg
        const distanceCost = routeInfo.distance * 1.5; // 1.5€ par km
        
        let priorityMultiplier = 1;
        switch (priorite) {
          case 'haute': priorityMultiplier = 1.2; break;
          case 'urgente': priorityMultiplier = 1.5; break;
        }
        
        const total = (baseCost + weightCost + distanceCost) * priorityMultiplier;
        setEstimatedCost(Math.round(total));
      }
    };

    calculateCost();
  }, [watchedValues.poids, watchedValues.priorite, routeInfo]);

  const onSubmit = (data) => {
    createMutation.mutate(data);
  };

  const handleRouteCalculated = (route) => {
    setRouteInfo(route);
  };

  const steps = [
    { id: 1, name: 'Marchandise', icon: TruckIcon },
    { id: 2, name: 'Adresses', icon: MapPinIcon },
    { id: 3, name: 'Détails', icon: CalendarIcon },
    { id: 4, name: 'Confirmation', icon: ScaleIcon },
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Progress Steps */}
      <div className="mb-8">
        <nav aria-label="Progress">
          <ol className="flex items-center justify-between">
            {steps.map((step, stepIdx) => (
              <li key={step.name} className="relative">
                <div className="flex items-center">
                  <div className={`
                    flex h-10 w-10 items-center justify-center rounded-full border-2 
                    ${currentStep >= step.id 
                      ? 'border-blue-600 bg-blue-600 text-white' 
                      : 'border-gray-300 bg-white text-gray-500'
                    }
                  `}>
                    <step.icon className="w-5 h-5" />
                  </div>
                  {stepIdx !== steps.length - 1 && (
                    <div className={`
                      hidden sm:block w-24 h-0.5 ml-4
                      ${currentStep > step.id ? 'bg-blue-600' : 'bg-gray-300'}
                    `} />
                  )}
                </div>
                <div className="mt-2">
                  <span className={`
                    text-sm font-medium
                    ${currentStep >= step.id ? 'text-blue-600' : 'text-gray-500'}
                  `}>
                    {step.name}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        </nav>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Step 1: Marchandise */}
        {currentStep === 1 && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6"
          >
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
              Informations sur la marchandise
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Type de marchandise *
                </label>
                <Controller
                  name="type_marchandise"
                  control={control}
                  render={({ field }) => (
                    <select
                      {...field}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    >
                      <option value="">Sélectionner le type</option>
                      {TYPES_MARCHANDISE.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  )}
                />
                {errors.type_marchandise && (
                  <p className="mt-1 text-sm text-red-600">{errors.type_marchandise.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Poids (kg) *
                </label>
                <Controller
                  name="poids"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="number"
                      min="0.1"
                      step="0.1"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Ex: 25.5"
                    />
                  )}
                />
                {errors.poids && (
                  <p className="mt-1 text-sm text-red-600">{errors.poids.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Volume (m³)
                </label>
                <Controller
                  name="volume"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="number"
                      min="0.1"
                      step="0.1"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Ex: 2.5"
                    />
                  )}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Valeur déclarée (€)
                </label>
                <Controller
                  name="valeur_declaree"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="number"
                      min="0"
                      step="0.01"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Ex: 1500.00"
                    />
                  )}
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description
                </label>
                <Controller
                  name="description"
                  control={control}
                  render={({ field }) => (
                    <textarea
                      {...field}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Description détaillée de la marchandise..."
                    />
                  )}
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Priorité *
                </label>
                <Controller
                  name="priorite"
                  control={control}
                  render={({ field }) => (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {PRIORITES.map((priorite) => (
                        <label
                          key={priorite.value}
                          className={`
                            relative flex cursor-pointer rounded-lg border p-4 focus:outline-none
                            ${field.value === priorite.value
                              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                              : 'border-gray-300 bg-white dark:bg-gray-700 dark:border-gray-600'
                            }
                          `}
                        >
                          <input
                            {...field}
                            type="radio"
                            value={priorite.value}
                            className="sr-only"
                          />
                          <span className="flex flex-1 flex-col">
                            <span className={`block text-sm font-medium ${priorite.color}`}>
                              {priorite.label}
                            </span>
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                />
              </div>
            </div>
          </motion.div>
        )}

        {/* Step 2: Adresses */}
        {currentStep === 2 && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                Adresse d'enlèvement
              </h2>
              <AdresseForm
                name="adresse_enlevement"
                control={control}
                errors={errors.adresse_enlevement}
              />
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                Adresse de livraison
              </h2>
              <AdresseForm
                name="adresse_livraison"
                control={control}
                errors={errors.adresse_livraison}
              />
            </div>

            {/* Carte avec itinéraire */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Aperçu de l'itinéraire
              </h3>
              <GoogleMap
                pickup={watchedValues.adresse_enlevement}
                delivery={watchedValues.adresse_livraison}
                onRouteCalculated={handleRouteCalculated}
                height="400px"
              />
              
              {routeInfo && (
                <div className="mt-4 grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <span className="block text-2xl font-bold text-blue-600">
                      {routeInfo.distance} km
                    </span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Distance</span>
                  </div>
                  <div className="text-center">
                    <span className="block text-2xl font-bold text-green-600">
                      {routeInfo.duration}
                    </span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Durée estimée</span>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Step 3: Détails */}
        {currentStep === 3 && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6"
          >
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
              Détails et contacts
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Contact enlèvement
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Nom du contact
                    </label>
                    <Controller
                      name="contact_enlevement"
                      control={control}
                      render={({ field }) => (
                        <input
                          {...field}
                          type="text"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                          placeholder="Nom de la personne à contacter"
                        />
                      )}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Téléphone
                    </label>
                    <Controller
                      name="telephone_enlevement"
                      control={control}
                      render={({ field }) => (
                        <input
                          {...field}
                          type="tel"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                          placeholder="+212 6 XX XX XX XX"
                        />
                      )}
                    />
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Contact livraison
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Nom du contact
                    </label>
                    <Controller
                      name="contact_livraison"
                      control={control}
                      render={({ field }) => (
                        <input
                          {...field}
                          type="text"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                          placeholder="Nom de la personne à contacter"
                        />
                      )}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Téléphone
                    </label>
                    <Controller
                      name="telephone_livraison"
                      control={control}
                      render={({ field }) => (
                        <input
                          {...field}
                          type="tel"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                          placeholder="+212 6 XX XX XX XX"
                        />
                      )}
                    />
                  </div>
                </div>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Instructions spéciales
                </label>
                <Controller
                  name="instructions_speciales"
                  control={control}
                  render={({ field }) => (
                    <textarea
                      {...field}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Instructions particulières pour l'enlèvement ou la livraison..."
                    />
                  )}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Date d'enlèvement souhaitée
                </label>
                <Controller
                  name="date_enlevement_prevue"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="datetime-local"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                  )}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Date de livraison souhaitée
                </label>
                <Controller
                  name="date_livraison_prevue"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="datetime-local"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                  )}
                />
              </div>
            </div>
          </motion.div>
        )}

        {/* Step 4: Confirmation */}
        {currentStep === 4 && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            {/* Estimation de prix */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100">
                    Estimation du coût
                  </h3>
                  <p className="text-blue-700 dark:text-blue-300">
                    Prix estimé basé sur les informations fournies
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-3xl font-bold text-blue-600">
                    {estimatedCost ? `${estimatedCost} €` : 'Calcul...'}
                  </span>
                  <p className="text-sm text-blue-600">HT</p>
                </div>
              </div>
            </div>

            {/* Résumé */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Résumé de la commande
              </h3>
              
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Type de marchandise:</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {TYPES_MARCHANDISE.find(t => t.value === watchedValues.type_marchandise)?.label}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Poids:</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {watchedValues.poids} kg
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Priorité:</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {PRIORITES.find(p => p.value === watchedValues.priorite)?.label}
                  </span>
                </div>
                {routeInfo && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Distance:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {routeInfo.distance} km
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Durée estimée:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {routeInfo.duration}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Avertissement */}
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg p-4">
              <div className="flex">
                <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                    Important
                  </h3>
                  <div className="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
                    <ul className="list-disc pl-5 space-y-1">
                      <li>Le prix affiché est une estimation qui peut varier selon les conditions réelles.</li>
                      <li>Un transporteur vous sera assigné dans les plus brefs délais.</li>
                      <li>Vous recevrez des notifications pour chaque étape du transport.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Navigation buttons */}
        <div className="flex justify-between pt-6">
          <button
            type="button"
            onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
            disabled={currentStep === 1}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Précédent
          </button>

          {currentStep < 4 ? (
            <button
              type="button"
              onClick={() => setCurrentStep(Math.min(4, currentStep + 1))}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
            >
              Suivant
            </button>
          ) : (
            <button
              type="submit"
              disabled={!isValid || createMutation.isLoading}
              className="px-6 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {createMutation.isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Création...
                </>
              ) : (
                'Créer la commande'
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

export default CreateCommande;