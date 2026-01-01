// services/api.ts
import axios from 'axios';
// ----------------------------------------------------------------------
// DÜZELTME: .web uzantısını SİLDİK.
// Artık hem web hem mobil için doğru dosya otomatik seçilecek.
import { getToken } from '../storage/storage';
// ----------------------------------------------------------------------
import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Bilgisayarınızın IP adresini buraya yazın
const COMPUTER_IP = '192.168.8.72'; 

const API_BASE_URL = __DEV__ 
  ? `http://${COMPUTER_IP}:8000/` // Geliştirme ortamı
  : 'https://your-production-api.com/'; // Canlı ortam

console.log('🔗 API Base URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  timeout: 15000,
});

// Request interceptor
api.interceptors.request.use(
  async (config) => {
    try {
      // Platform bağımsız token alma fonksiyonu
      const token = await getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('❌ Error getting token:', error);
    }
    
    // Logları sadece geliştirme ortamında göster
    if (__DEV__) {
        console.log('📤 Request:', config.method?.toUpperCase(), config.url);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    if (__DEV__) {
        console.log('✅ Response:', response.status, response.config.url);
    }
    return response;
  },
  (error) => {
    if (error.response) {
      console.error('❌ Server Error:', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('❌ Network Error - No Response. Is the backend running?');
    } else {
      console.error('❌ Request Setup Error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

// API Exportları (Değişmedi, sadece referans için kısaca tuttum)
export const wishlistAPI = {
  getWishlist: () => api.get('api/wishlist/'),
  addItem: (productId: number, note?: string) => api.post('api/wishlist/add-item/', { product_id: productId, note, notify_on_price_drop: true, notify_on_restock: true }),
  removeItem: (productId: number) => api.delete(`api/wishlist/remove-item/${productId}/`),
  checkItem: (productId: number) => api.get(`api/wishlist/check/${productId}/`),
};

export const viewHistoryAPI = {
  getHistory: () => api.get('api/view-history/'),
  recordView: (productId: number) => api.post('api/view-history/record/', { product_id: productId }),
  clearHistory: () => api.delete('api/view-history/clear/'),
};

export const reviewAPI = {
  getMyReviews: () => api.get('api/reviews/'),
  getProductReviews: (productId: number) => api.get(`api/reviews/product/${productId}/`),
  addReview: (productId: number, rating: number, comment?: string) => api.post('api/reviews/', { product: productId, rating, comment: comment || '' }),
  updateReview: (reviewId: number, rating: number, comment?: string) => api.patch(`api/reviews/${reviewId}/`, { rating, comment }),
  deleteReview: (reviewId: number) => api.delete(`api/reviews/${reviewId}/`),
};

export const serviceRequestAPI = {
  getMyRequests: () => api.get('api/service-requests/'),
  createRequest: (productOwnershipId: number, requestType: string, description: string) => api.post('api/service-requests/', { product_ownership: productOwnershipId, request_type: requestType, description }),
  getRequestDetail: (requestId: number) => api.get(`api/service-requests/${requestId}/`),
  getQueueStatus: () => api.get('api/service-requests/queue-status/'),
};

export const notificationAPI = {
  getNotifications: () => api.get('api/notifications/'),
  getUnreadCount: () => api.get('api/notifications/unread-count/'),
  markAsRead: (notificationId: number) => api.post(`api/notifications/${notificationId}/read/`),
  markAllAsRead: () => api.post('api/notifications/read-all/'),
  getSettings: () => api.get('api/notification-settings/'),
  updateSettings: (settings: any) => api.patch('api/notification-settings/', settings),
};

export const recommendationAPI = {
  getRecommendations: () => api.get('api/recommendations/'),
  generateRecommendations: () => api.post('api/recommendations/generate/'),
  recordClick: (recommendationId: number) => api.post(`api/recommendations/${recommendationId}/click/`),
};

export const productOwnershipAPI = {
  getMyProducts: () => api.get('api/my-products/'),
  getMyOwnerships: () => api.get('api/product-ownerships/my-ownerships/'),
  getOwnershipDetail: (ownershipId: number) => api.get(`api/product-ownerships/${ownershipId}/`),
};

export default api;