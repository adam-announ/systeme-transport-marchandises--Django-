import api from './api';

export const transporteurService = {
  getAll: async (params = {}) => {
    const response = await api.get('/transporteurs/', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/transporteurs/${id}/`);
    return response.data;
  },

  getAvailable: async (params = {}) => {
    const response = await api.get('/transporteurs/disponibles/', { params });
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

  getMissions: async (id, params = {}) => {
    const response = await api.get(`/transporteurs/${id}/missions/`, { params });
    return response.data;
  },

  acceptMission: async (transporteurId, commandeId) => {
    const response = await api.post(`/transporteurs/${transporteurId}/accepter-mission/`, {
      commande_id: commandeId,
    });
    return response.data;
  },

  refuseMission: async (transporteurId, commandeId, raison) => {
    const response = await api.post(`/transporteurs/${transporteurId}/refuser-mission/`, {
      commande_id: commandeId,
      raison,
    });
    return response.data;
  },

  getStatistics: async (id) => {
    const response = await api.get(`/transporteurs/${id}/statistiques/`);
    return response.data;
  },
};