import axios from 'axios';
import { getToken, clearAllTokens } from '../storage/storage.native';
import { router } from 'expo-router';
import Constants from 'expo-constants';

// 🔹 API URL Configuration
// Uses environment variables - set EXPO_PUBLIC_API_URL in .env file
// Default fallback for development
const getApiUrl = () => {
  // Check for Expo environment variable (EXPO_PUBLIC_ prefix is auto-exposed)
  const envUrl = process.env.EXPO_PUBLIC_API_URL;

  if (envUrl) {
    return envUrl;
  }

  // Fallback: try to detect local IP from Expo manifest
  const debuggerHost = Constants.expoConfig?.hostUri?.split(':')[0];
  if (debuggerHost) {
    return `http://${debuggerHost}:8000/`;
  }

  // Production fallback
  return process.env.EXPO_PUBLIC_PROD_API_URL || 'https://api.bekosirs.com/';
};

const API_BASE_URL = getApiUrl();

console.log('🔗 API Base URL:', API_BASE_URL);
console.log('📱 Device:', Constants.deviceName);
console.log('🌐 Platform:', Constants.platform);


const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  timeout: 30000, // 30 second timeout for mobile networks and heavy ML ops
});

// Request interceptor
api.interceptors.request.use(
  async (config) => {
    try {
      const token = await getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log('✅ Token added to request');
      }
    } catch (error) {
      console.error('❌ Error getting token:', error);
    }

    console.log('📤 Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor with detailed error logging
api.interceptors.response.use(
  (response) => {
    console.log('✅ Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('❌ Server Error:', {
        status: error.response.status,
        data: error.response.data,
        url: error.config?.url
      });

      // 401 Unauthorized Handling
      if (error.response.status === 401) {
        console.warn('🔒 Session expired (401), clearing tokens and redirecting to login...');
        clearAllTokens().then(() => {
          // Use Replace to prevent going back
          router.replace('/login');
        });
      }
    } else if (error.request) {
      // Request made but no response received
      console.error('❌ Network Error - No Response:', {
        message: 'Cannot connect to backend',
        url: error.config?.url,
        baseURL: API_BASE_URL
      });
      console.error('💡 Troubleshooting:');
      console.error('   1. Check if backend is running: python manage.py runserver 0.0.0.0:8000');
      console.error('   2. Verify EXPO_PUBLIC_API_URL in .env file');
      console.error('   3. Ensure phone and computer are on same WiFi');
      console.error('   4. Current API URL:', API_BASE_URL);
      console.error('   5. Disable firewall temporarily to test');
    } else {
      // Error in request setup
      console.error('❌ Request Setup Error:', error.message);
    }

    // Return a more user-friendly error
    const userError = error.response?.data?.message ||
      error.response?.statusText ||
      'Network connection error. Check your connection.';

    return Promise.reject({
      ...error,
      userMessage: userError
    });
  }
);

// Test connection function
export const testBackendConnection = async () => {
  try {
    console.log('🔍 Testing backend connection...');
    const response = await axios.get(`${API_BASE_URL}admin/`, {
      timeout: 5000,
      validateStatus: () => true // Accept any status to test connectivity
    });
    console.log('✅ Backend is reachable! Status:', response.status);
    return true;
  } catch (error: any) {
    console.error('❌ Backend connection test failed:');
    if (error.code === 'ECONNABORTED') {
      console.error('   ⏱️ Connection timeout - Backend not responding');
    } else if (error.code === 'ENOTFOUND') {
      console.error('   🌐 DNS resolution failed - Check IP address');
    } else if (error.message.includes('Network Error')) {
      console.error('   📡 Network error - Check WiFi connection');
    } else {
      console.error('   ❓ Unknown error:', error.message);
    }
    return false;
  }
};

// ----------------------------------------
// 🔹 WISHLIST API
// ----------------------------------------
export const wishlistAPI = {
  // İstek listesini getir
  getWishlist: () => api.get('api/wishlist/'),

  // Ürün ekle
  addItem: (productId: number, note?: string) =>
    api.post('api/wishlist/add-item/', {
      product_id: productId,
      note: note || '',
      notify_on_price_drop: true,
      notify_on_restock: true,
    }),

  // Ürün çıkar
  removeItem: (productId: number) =>
    api.delete(`api/wishlist/remove-item/${productId}/`),

  // Ürün listede mi kontrol et
  checkItem: (productId: number) =>
    api.get(`api/wishlist/check/${productId}/`),

  // Ürün güncelle (Bildirim ayarları vb.)
  updateItem: (productId: number, data: { notify_on_price_drop?: boolean; notify_on_restock?: boolean; note?: string }) =>
    api.patch(`api/wishlist/update-item/${productId}/`, data),
};

// ----------------------------------------
// 🔹 VIEW HISTORY API
// ----------------------------------------
export const viewHistoryAPI = {
  // Görüntüleme geçmişini getir
  getHistory: () => api.get('api/view-history/'),

  // Görüntüleme kaydet
  recordView: (productId: number) =>
    api.post('api/view-history/record/', { product_id: productId }),

  // Geçmişi temizle
  clearHistory: () => api.delete('api/view-history/clear/'),
};

// ----------------------------------------
// 🔹 REVIEW API
// ----------------------------------------
export const reviewAPI = {
  // Kullanıcının yorumlarını getir
  getMyReviews: () => api.get('api/reviews/'),

  // Ürüne ait yorumları getir
  getProductReviews: (productId: number) =>
    api.get(`api/reviews/product/${productId}/`),

  // Yorum ekle
  addReview: (productId: number, rating: number, comment?: string) =>
    api.post('api/reviews/', {
      product: productId,
      rating,
      comment: comment || '',
    }),

  // Yorumu güncelle
  updateReview: (reviewId: number, rating: number, comment?: string) =>
    api.patch(`api/reviews/${reviewId}/`, { rating, comment }),

  // Yorumu sil
  deleteReview: (reviewId: number) => api.delete(`api/reviews/${reviewId}/`),
};

// ----------------------------------------
// 🔹 SERVICE REQUEST API
// ----------------------------------------
export const serviceRequestAPI = {
  // Servis taleplerimi getir
  getMyRequests: () => api.get('api/service-requests/'),

  // Yeni talep oluştur
  createRequest: (
    productOwnershipId: number,
    requestType: 'repair' | 'maintenance' | 'warranty' | 'complaint' | 'other',
    description: string
  ) =>
    api.post('api/service-requests/', {
      product_ownership: productOwnershipId,
      request_type: requestType,
      description,
    }),

  // Talep detayını getir
  getRequestDetail: (requestId: number) =>
    api.get(`api/service-requests/${requestId}/`),

  // Kuyruk durumunu getir
  getQueueStatus: () => api.get('api/service-requests/queue-status/'),
};

// ----------------------------------------
// 🔹 NOTIFICATION API
// ----------------------------------------
export const notificationAPI = {
  // Bildirimleri getir
  getNotifications: () => api.get('api/notifications/'),

  // Okunmamış bildirim sayısı
  getUnreadCount: () => api.get('api/notifications/unread-count/'),

  // Bildirimi okundu işaretle
  markAsRead: (notificationId: number) =>
    api.post(`api/notifications/${notificationId}/read/`),

  // Tümünü okundu işaretle
  markAllAsRead: () => api.post('api/notifications/read-all/'),

  // Bildirim ayarlarını getir
  getSettings: () => api.get('api/profile/notification-settings/'),

  // Bildirim ayarlarını güncelle
  updateSettings: (settings: {
    notify_service_updates?: boolean;
    notify_price_drops?: boolean;
    notify_restock?: boolean;
    notify_recommendations?: boolean;
    notify_warranty_expiry?: boolean;
    notify_general?: boolean;
  }) => api.patch('api/profile/notification-settings/', settings),
};

// ----------------------------------------
// 🔹 RECOMMENDATION API
// ----------------------------------------
export const recommendationAPI = {
  // Önerileri getir
  getRecommendations: (refresh?: boolean) => api.get(refresh ? 'api/recommendations/?refresh=true' : 'api/recommendations/'),

  // Yeni öneriler oluştur
  generateRecommendations: () => api.post('api/recommendations/generate/'),

  // Öneri tıklaması kaydet
  recordClick: (recommendationId: number) =>
    api.post(`api/recommendations/${recommendationId}/click/`),
};

// ----------------------------------------
// 🔹 PRODUCT OWNERSHIP API
// ----------------------------------------
export const productOwnershipAPI = {
  // Sahip olduğum ürünleri getir (basit liste - my-products sayfası için)
  getMyProducts: () => api.get('api/my-products/'),

  // Sahip olduğum ürünleri garanti bilgileriyle getir (servis talepleri için)
  getMyOwnerships: () => api.get('api/product-ownerships/my-ownerships/'),

  // Ürün sahipliği detayı
  getOwnershipDetail: (ownershipId: number) =>
    api.get(`api/product-ownerships/${ownershipId}/`),
};

export default api;