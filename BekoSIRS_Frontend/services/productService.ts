import api from './api';

// ─────────────────────────────────────────
// 🔹 PRODUCT API
// ─────────────────────────────────────────
export const productAPI = {
    getPopularProducts: () => api.get('api/v1/products/popular/'),
};
