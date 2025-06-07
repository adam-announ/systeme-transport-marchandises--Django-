import axios from 'axios';

// Configuration de base d'Axios
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour ajouter le token d'authentification
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Intercepteur pour gérer les erreurs de réponse
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Service des incidents
export const incidentService = {
  getAll: async (params = {}) => {
    const response = await api.get('/incidents/', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/incidents/${id}/`);
    return response.data;
  },

  create: async (data) => {
    const formData = new FormData();
    Object.keys(data).forEach(key => {
      if (data[key] !== null && data[key] !== undefined) {
        formData.append(key, data[key]);
      }
    });
    
    const response = await api.post('/incidents/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`/incidents/${id}/`, data);
    return response.data;
  },

  resolve: async (id, commentaire) => {
    const response = await api.post(`/incidents/${id}/resolve/`, {
      resolution_commentaire: commentaire,
    });
    return response.data;
  },
};

// Service des notifications
export const notificationService = {
  getAll: async (params = {}) => {
    const response = await api.get('/notifications/', { params });
    return response.data;
  },

  getUnread: async () => {
    const response = await api.get('/notifications/non_lues/');
    return response.data;
  },

  markAsRead: async (id) => {
    const response = await api.post(`/notifications/${id}/marquer_lue/`);
    return response.data;
  },

  markAllAsRead: async () => {
    const response = await api.post('/notifications/marquer_toutes_lues/');
    return response.data;
  },
};

// Service du tableau de bord
export const dashboardService = {
  getClientDashboard: async () => {
    const response = await api.get('/dashboard/client/');
    return response.data;
  },

  getTransporteurDashboard: async () => {
    const response = await api.get('/dashboard/transporteur/');
    return response.data;
  },

  getAdminDashboard: async () => {
    const response = await api.get('/dashboard/admin/');
    return response.data;
  },

  getPlanificateurDashboard: async () => {
    const response = await api.get('/dashboard/planificateur/');
    return response.data;
  },
};

// Service de planification
export const planificationService = {
  assignationAutomatique: async (data) => {
    const response = await api.post('/assignation-automatique/', data);
    return response.data;
  },

  optimiserItineraires: async (data) => {
    const response = await api.post('/optimiser-itineraires/', data);
    return response.data;
  },

  calculerItineraire: async (origine, destination, waypoints = []) => {
    const response = await api.post('/calculer-itineraire/', {
      origine,
      destination,
      waypoints,
    });
    return response.data;
  },
};

// Service des clients
export const clientService = {
  getAll: async (params = {}) => {
    const response = await api.get('/clients/', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/clients/${id}/`);
    return response.data;
  },

  create: async (data) => {
    const response = await api.post('/clients/', data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`/clients/${id}/`, data);
    return response.data;
  },

  delete: async (id) => {
    await api.delete(`/clients/${id}/`);
  },
};

// Service des paramètres
export const parametresService = {
  getAll: async () => {
    const response = await api.get('/parametres/');
    return response.data;
  },

  update: async (nom, valeur) => {
    const response = await api.patch(`/parametres/${nom}/`, { valeur });
    return response.data;
  },
};

// Service de géolocalisation
export const geoService = {
  getCurrentPosition: () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Géolocalisation non supportée'));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          });
        },
        (error) => {
          reject(error);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000, // 5 minutes
        }
      );
    });
  },

  watchPosition: (callback, errorCallback) => {
    if (!navigator.geolocation) {
      errorCallback(new Error('Géolocalisation non supportée'));
      return null;
    }

    return navigator.geolocation.watchPosition(
      (position) => {
        callback({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp,
        });
      },
      errorCallback,
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000, // 1 minute
      }
    );
  },

  clearWatch: (watchId) => {
    if (navigator.geolocation && watchId) {
      navigator.geolocation.clearWatch(watchId);
    }
  },
};

// Service de upload de fichiers
export const uploadService = {
  uploadImage: async (file, folder = 'general') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', folder);

    const response = await api.post('/upload/image/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  uploadDocument: async (file, folder = 'documents') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', folder);

    const response = await api.post('/upload/document/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

// Service d'export
export const exportService = {
  exportCommandes: async (format = 'csv', filters = {}) => {
    const response = await api.get('/export/commandes/', {
      params: { format, ...filters },
      responseType: 'blob',
    });
    
    const blob = new Blob([response.data], { 
      type: format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
    
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `commandes.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  exportTransporteurs: async (format = 'csv') => {
    const response = await api.get('/export/transporteurs/', {
      params: { format },
      responseType: 'blob',
    });
    
    const blob = new Blob([response.data], { 
      type: format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
    
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `transporteurs.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  generateReport: async (type, params = {}) => {
    const response = await api.get(`/reports/${type}/`, {
      params,
      responseType: 'blob',
    });
    
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `rapport_${type}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};

// Service WebSocket pour les notifications en temps réel
class WebSocketService {
  constructor() {
    this.socket = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect(token) {
    const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/ws/notifications/?token=${token}`;
    
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connecté');
      this.reconnectAttempts = 0;
    };

    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.socket.onclose = (event) => {
      console.log('WebSocket fermé', event);
      this.handleReconnect();
    };

    this.socket.onerror = (error) => {
      console.error('Erreur WebSocket:', error);
    };
  }

  handleMessage(data) {
    const { type } = data;
    if (this.listeners[type]) {
      this.listeners[type].forEach(callback => callback(data));
    }
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        const token = localStorage.getItem('token');
        if (token) {
          this.connect(token);
        }
      }, 1000 * this.reconnectAttempts);
    }
  }

  on(eventType, callback) {
    if (!this.listeners[eventType]) {
      this.listeners[eventType] = [];
    }
    this.listeners[eventType].push(callback);
  }

  off(eventType, callback) {
    if (this.listeners[eventType]) {
      this.listeners[eventType] = this.listeners[eventType].filter(cb => cb !== callback);
    }
  }

  send(message) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export const webSocketService = new WebSocketService();

// Utilitaires d'erreur
export const handleApiError = (error) => {
  if (error.response) {
    // Le serveur a répondu avec un statut d'erreur
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return data.message || 'Données invalides';
      case 401:
        return 'Non autorisé - Veuillez vous reconnecter';
      case 403:
        return 'Accès interdit';
      case 404:
        return 'Ressource non trouvée';
      case 500:
        return 'Erreur serveur - Veuillez réessayer plus tard';
      default:
        return data.message || 'Une erreur est survenue';
    }
  } else if (error.request) {
    // La requête a été faite mais pas de réponse
    return 'Erreur de connexion - Vérifiez votre connexion internet';
  } else {
    // Autre erreur
    return error.message || 'Une erreur inattendue est survenue';
  }
};

export default api; dauthentification
export const authService = {
  login: async (credentials) => {
    const response = await api.post('/auth/login/', credentials);
    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/auth/register/', userData);
    return response.data;
  },

  logout: async () => {
    await api.post('/auth/logout/');
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/user/');
    return response.data;
  },

  refreshToken: async () => {
    const response = await api.post('/auth/refresh/');
    return response.data;
  },
};

// Service des commandes
export const commandeService = {
  getAll: async (params = {}) => {
    const response = await api.get('/commandes/', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/commandes/${id}/`);
    return response.data;
  },

  create: async (data) => {
    const response = await api.post('/commandes/', data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`/commandes/${id}/`, data);
    return response.data;
  },

  delete: async (id) => {
    await api.delete(`/commandes/${id}/`);
  },

  assignTransporteur: async (commandeId, transporteurId) => {
    const response = await api.post(`/commandes/${commandeId}/assigner_transporteur/`, {
      transporteur_id: transporteurId,
    });
    return response.data;
  },

  changeStatus: async (commandeId, status, data = {}) => {
    const response = await api.post(`/commandes/${commandeId}/changer_statut/`, {
      statut: status,
      ...data,
    });
    return response.data;
  },

  getTracking: async (commandeId) => {
    const response = await api.get(`/commandes/${commandeId}/tracking/`);
    return response.data;
  },

  getStatistics: async () => {
    const response = await api.get('/commandes/statistiques/');
    return response.data;
  },
};

// Service des transporteurs
export const transporteurService = {
  getAll: async (params = {}) => {
    const response = await api.get('/transporteurs/', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/transporteurs/${id}/`);
    return response.data;
  },

  getAvailable: async () => {
    const response = await api.get('/transporteurs/disponibles/');
    return response.data;
  },

  toggleDisponibilite: async (id) => {
    const response = await api.post(`/transporteurs/${id}/toggle_disponibilite/`);
    return response.data;
  },

  updatePosition: async (id, latitude, longitude) => {
    const response = await api.post(`/transporteurs/${id}/update_position/`, {
      latitude,
      longitude,
    });
    return response.data;
  },

  create: async (data) => {
    const response = await api.post('/transporteurs/', data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`/transporteurs/${id}/`, data);
    return response.data;
  },
};

export default api;

// Service d'authentification (à la fin du fichier)
export const authService = {
  login: async (credentials) => {
    const response = await api.post('/auth/login/', credentials);
    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/auth/register/', userData);
    return response.data;
  },

  logout: async () => {
    await api.post('/auth/logout/');
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/user/');
    return response.data;
  },

  refreshToken: async () => {
    const response = await api.post('/auth/refresh/');
    return response.data;
  },
};

// Service des commandes (à la fin du fichier)
export const commandeService = {
  getAll: async (params = {}) => {
    const response = await api.get('/commandes/', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/commandes/${id}/`);
    return response.data;
  },

  create: async (data) => {
    const response = await api.post('/commandes/', data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`/commandes/${id}/`, data);
    return response.data;
  },

  delete: async (id) => {
    await api.delete(`/commandes/${id}/`);
  },

  assignTransporteur: async (commandeId, transporteurId) => {
    const response = await api.post(`/commandes/${commandeId}/assigner-transporteur/`, {
      transporteur_id: transporteurId,
    });
    return response.data;
  },

  changeStatus: async (commandeId, status, data = {}) => {
    const response = await api.post(`/commandes/${commandeId}/changer-statut/`, {
      statut: status,
      ...data,
    });
    return response.data;
  },

  getTracking: async (commandeId) => {
    const response = await api.get(`/commandes/${commandeId}/tracking/`);
    return response.data;
  },

  getStatistics: async () => {
    const response = await api.get('/commandes/statistiques/');
    return response.data;
  },
};

// Service des transporteurs (à la fin du fichier)
export const transporteurService = {
  getAll: async (params = {}) => {
    const response = await api.get('/transporteurs/', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/transporteurs/${id}/`);
    return response.data;
  },

  getAvailable: async () => {
    const response = await api.get('/transporteurs/disponibles/');
    return response.data;
  },

  toggleDisponibilite: async (id) => {
    const response = await api.post(`/transporteurs/${id}/toggle_disponibilite/`);
    return response.data;
  },

  updatePosition: async (id, latitude, longitude) => {
    const response = await api.post(`/transporteurs/${id}/update_position/`, {
      latitude,
      longitude,
    });
    return response.data;
  },

  create: async (data) => {
    const response = await api.post('/transporteurs/', data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`/transporteurs/${id}/`, data);
    return response.data;
  },

  delete: async (id) => {
    await api.delete(`/transporteurs/${id}/`);
  },
};