import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
};

export const voiceApi = {
    // Send voice call
    sendCall: async (callData) => {
        const response = await axios.post(`${API}/voice/call`, callData, {
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Get call history
    getHistory: async (limit = 50, skip = 0) => {
        const response = await axios.get(`${API}/voice/history`, {
            params: { limit, skip },
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Get call statistics
    getStats: async () => {
        const response = await axios.get(`${API}/voice/stats`, {
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Get single call details
    getCall: async (callId) => {
        const response = await axios.get(`${API}/voice/call/${callId}`, {
            headers: getAuthHeaders()
        });
        return response.data;
    }
};

export const authApi = {
    login: async (email, password) => {
        const response = await axios.post(`${API}/auth/login`, { email, password });
        return response.data;
    },

    register: async (email, password, name) => {
        const response = await axios.post(`${API}/auth/register`, { email, password, name });
        return response.data;
    },

    getMe: async () => {
        const response = await axios.get(`${API}/auth/me`, {
            headers: getAuthHeaders()
        });
        return response.data;
    }
};
