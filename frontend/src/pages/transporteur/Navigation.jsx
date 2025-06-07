// frontend/src/pages/transporteur/Navigation.jsx
// ================================
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import {
  MapPinIcon,
  PhoneIcon,
  NavigationIcon,
} from '@heroicons/react/24/outline';

import { commandeService } from '../../services/commandes';
import GoogleMap from '../../components/maps/GoogleMap';
import Loading from '../../components/common/Loading';

const Navigation = () => {
  const { commandeId } = useParams();
  const [currentPosition, setCurrentPosition] = useState(null);

  const { data: commande, isLoading } = useQuery(
    ['commande', commandeId],
    () => commandeService.getById(commandeId)
  );

  useEffect(() => {
    if (navigator.geolocation) {
      const watchId = navigator.geolocation.watchPosition(
        (position) => {
          setCurrentPosition({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        (error) => console.error('Erreur géolocalisation:', error),
        { enableHighAccuracy: true, maximumAge: 10000 }
      );

      return () => navigator.geolocation.clearWatch(watchId);
    }
  }, []);

  if (isLoading) return <Loading />;
  if (!commande) return <div>Commande non trouvée</div>;

  const openGoogleMaps = (destination) => {
    const { lat, lng } = destination;
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`;
    window.open(url, '_blank');
  };

  return (
    <div className="p-6 space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Navigation - Commande #{commande.numero}
        </h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center">
              <MapPinIcon className="w-5 h-5 mr-2 text-blue-600" />
              Enlèvement
            </h3>
            <div className="space-y-2">
              <p className="text-gray-900 dark:text-white">
                {commande.adresse_enlevement?.rue}
              </p>
              <p className="text-gray-600">
                {commande.adresse_enlevement?.ville}, {commande.adresse_enlevement?.code_postal}
              </p>
              {commande.contact_enlevement && (
                <div className="flex items-center space-x-2">
                  <PhoneIcon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm">{commande.contact_enlevement}</span>
                  {commande.telephone_enlevement && (
                    <a
                      href={`tel:${commande.telephone_enlevement}`}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      {commande.telephone_enlevement}
                    </a>
                  )}
                </div>
              )}
            </div>
            <button
              onClick={() => openGoogleMaps({
                lat: commande.adresse_enlevement?.latitude || 0,
                lng: commande.adresse_enlevement?.longitude || 0,
              })}
              className="mt-3 flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <NavigationIcon className="w-4 h-4 mr-2" />
              Naviguer vers l'enlèvement
            </button>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center">
              <MapPinIcon className="w-5 h-5 mr-2 text-green-600" />
              Livraison
            </h3>
            <div className="space-y-2">
              <p className="text-gray-900 dark:text-white">
                {commande.adresse_livraison?.rue}
              </p>
              <p className="text-gray-600">
                {commande.adresse_livraison?.ville}, {commande.adresse_livraison?.code_postal}
              </p>
              {commande.contact_livraison && (
                <div className="flex items-center space-x-2">
                  <PhoneIcon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm">{commande.contact_livraison}</span>
                  {commande.telephone_livraison && (
                    <a
                      href={`tel:${commande.telephone_livraison}`}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      {commande.telephone_livraison}
                    </a>
                  )}
                </div>
              )}
            </div>
            <button
              onClick={() => openGoogleMaps({
                lat: commande.adresse_livraison?.latitude || 0,
                lng: commande.adresse_livraison?.longitude || 0,
              })}
              className="mt-3 flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <NavigationIcon className="w-4 h-4 mr-2" />
              Naviguer vers la livraison
            </button>
          </div>
        </div>
      </div>

      {/* Carte */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold mb-4">Carte de navigation</h3>
        <div className="h-96">
          <GoogleMap
            pickup={commande.adresse_enlevement}
            delivery={commande.adresse_livraison}
            currentPosition={currentPosition}
            height="100%"
          />
        </div>
      </div>

      {/* Informations sur la marchandise */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold mb-4">Détails de la marchandise</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <span className="text-gray-600">Type:</span>
            <div className="font-medium">{commande.type_marchandise}</div>
          </div>
          <div>
            <span className="text-gray-600">Poids:</span>
            <div className="font-medium">{commande.poids} kg</div>
          </div>
          <div>
            <span className="text-gray-600">Priorité:</span>
            <div className="font-medium">{commande.priorite_display}</div>
          </div>
        </div>
        
        {commande.instructions_speciales && (
          <div className="mt-4">
            <span className="text-gray-600">Instructions spéciales:</span>
            <div className="mt-1 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
              {commande.instructions_speciales}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Navigation;
