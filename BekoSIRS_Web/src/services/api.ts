import axios from 'axios';

// Get the base URL from environment variables or default to localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor to add the auth token to every request
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor to handle common errors (like 401 Unauthorized)
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // If the error is 401 and we haven't already tried to refresh the token
        if (error.response && error.response.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const refreshToken = localStorage.getItem('refresh');
                if (refreshToken) {
                    // Attempt to refresh the token
                    // Note: You might need to adjust the refresh endpoint path if it differs
                    const response = await axios.post('http://127.0.0.1:8000/api/v1/token/refresh/', {
                        refresh: refreshToken,
                    });

                    if (response.status === 200) {
                        localStorage.setItem('access', response.data.access);
                        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`;
                        return api(originalRequest);
                    }
                }
            } catch (refreshError) {
                // If refresh fails, logout
                localStorage.removeItem('access');
                localStorage.removeItem('refresh');
                localStorage.removeItem('user_role');
                window.location.href = '/'; // Redirect to login
                return Promise.reject(refreshError);
            }
        }
        return Promise.reject(error);
    }
);

export default api;
