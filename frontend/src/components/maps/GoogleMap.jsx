import React, { useEffect, useRef, useState } from 'react';
import { Wrapper } from '@googlemaps/react-wrapper';

const MapComponent = ({ pickup, delivery, onRouteCalculated, height = '400px' }) => {
  const mapRef = useRef(null);
  const [map, setMap] = useState(null);
  const [directionsService, setDirectionsService] = useState(null);
  const [directionsRenderer, setDirectionsRenderer] = useState(null);

  useEffect(() => {
    if (mapRef.current && !map) {
      const newMap = new window.google.maps.Map(mapRef.current, {
        center: { lat: 33.5731, lng: -7.5898 }, // Casablanca par défaut
        zoom: 8,
        mapTypeControl: true,
        streetViewControl: true,
        fullscreenControl: true,
      });

      const service = new window.google.maps.DirectionsService();
      const renderer = new window.google.maps.DirectionsRenderer({
        draggable: false,
        panel: null,
      });

      renderer.setMap(newMap);

      setMap(newMap);
      setDirectionsService(service);
      setDirectionsRenderer(renderer);
    }
  }, [map]);

  useEffect(() => {
    if (pickup && delivery && directionsService && directionsRenderer && map) {
      calculateRoute();
    }
  }, [pickup, delivery, directionsService, directionsRenderer]);

  const calculateRoute = () => {
    if (!pickup?.ville || !delivery?.ville) return;

    const pickupAddress = `${pickup.rue || ''}, ${pickup.ville}, ${pickup.pays || 'Maroc'}`;
    const deliveryAddress = `${delivery.rue || ''}, ${delivery.ville}, ${delivery.pays || 'Maroc'}`;

    directionsService.route(
      {
        origin: pickupAddress,
        destination: deliveryAddress,
        travelMode: window.google.maps.TravelMode.DRIVING,
        unitSystem: window.google.maps.UnitSystem.METRIC,
        language: 'fr',
      },
      (result, status) => {
        if (status === 'OK') {
          directionsRenderer.setDirections(result);
          
          const route = result.routes[0];
          const leg = route.legs[0];
          
          const routeInfo = {
            distance: Math.round(leg.distance.value / 1000), // km
            duration: leg.duration.text,
            distanceText: leg.distance.text,
          };
          
          if (onRouteCalculated) {
            onRouteCalculated(routeInfo);
          }
        } else {
          console.error('Erreur de calcul d\'itinéraire:', status);
        }
      }
    );
  };

  return <div ref={mapRef} style={{ height, width: '100%' }} className="rounded-lg" />;
};

const GoogleMap = (props) => {
  const apiKey = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;
  
  if (!apiKey) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-100 dark:bg-gray-700 rounded-lg">
        <p className="text-gray-500 dark:text-gray-400">
          Clé API Google Maps non configurée
        </p>
      </div>
    );
  }

  return (
    <Wrapper apiKey={apiKey} libraries={['geometry', 'drawing', 'places']}>
      <MapComponent {...props} />
    </Wrapper>
  );
};

export default GoogleMap;
