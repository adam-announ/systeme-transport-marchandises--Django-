import api from './api';

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

  assignTransporteur: async ({ commandeId, transporteurId }) => {
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

  addTracking: async (commandeId, data) => {
    const response = await api.post(`/commandes/${commandeId}/tracking/`, data);
    return response.data;
  },

  getBonLivraison: async (commandeId) => {
    const response = await api.get(`/commandes/${commandeId}/bon-livraison/`);
    return response.data;
  },

  signBonLivraison: async (commandeId, signature) => {
    const response = await api.post(`/commandes/${commandeId}/bon-livraison/signer/`, {
      signature,
    });
    return response.data;
  },

  calculatePrice: async (data) => {
    const response = await api.post('/commandes/calculer-prix/', data);
    return response.data;
  },

  getStatistics: async (params = {}) => {
    const response = await api.get('/commandes/statistiques/', { params });
    return response.data;
  },
};