import api from './api';

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
    try {
      await api.post('/auth/logout/');
    } catch (error) {
      // Continue même si l'appel échoue
    }
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/user/');
    return response.data;
  },

  refreshToken: async () => {
    const response = await api.post('/auth/refresh/');
    return response.data;
  },

  updateProfile: async (data) => {
    const response = await api.patch('/auth/user/', data);
    return response.data;
  },

  changePassword: async (data) => {
    const response = await api.post('/auth/change-password/', data);
    return response.data;
  },
};