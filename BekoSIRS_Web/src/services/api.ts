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

// ----------------------------------------
// Installment API Functions (Taksit Sistemi)
// ----------------------------------------
export const installmentAPI = {
    // Get all installment plans with optional filters
    getAllPlans: (filters?: { status?: string; customer?: number }) => {
        const params = new URLSearchParams();
        if (filters?.status) params.append('status', filters.status);
        if (filters?.customer) params.append('customer', filters.customer.toString());
        const queryString = params.toString();
        return api.get(`/installment-plans/${queryString ? `?${queryString}` : ''}`);
    },

    // Get plan details
    getPlanDetail: (planId: number) => api.get(`/installment-plans/${planId}/`),

    // Get plan installments
    getPlanInstallments: (planId: number) => api.get(`/installment-plans/${planId}/installments/`),

    // Get overdue plans
    getOverduePlans: () => api.get('/installment-plans/overdue/'),

    // Create new installment plan
    createPlan: (data: {
        customer: number;
        product: number;
        total_amount: number;
        down_payment?: number;
        installment_count: number;
        start_date: string;
        equal_installments?: boolean;
        installments?: Array<{ amount: number; due_date?: string }>;
        notes?: string;
    }) => api.post('/installment-plans/', data),

    // Cancel plan
    cancelPlan: (planId: number) => api.post(`/installment-plans/${planId}/cancel/`),

    // Admin approve payment
    adminApprovePayment: (installmentId: number, paymentDate?: string) =>
        api.post(`/installments/${installmentId}/admin-approve/`, { payment_date: paymentDate }),

    // Get overdue installments list
    getOverdueInstallments: () => api.get('/installments/overdue-list/'),

    // Get pending confirmations (awaiting admin approval)
    getPendingConfirmations: () => api.get('/installments/pending-confirmations/'),
};

// ----------------------------------------
// Product API Functions (Ürün Yönetimi)
// ----------------------------------------
export const productAPI = {
    // Get all products with optional filters
    getAll: (filters?: { category?: number; search?: string; brand?: string }) => {
        const params = new URLSearchParams();
        if (filters?.category) params.append('category', filters.category.toString());
        if (filters?.search) params.append('search', filters.search);
        if (filters?.brand) params.append('brand', filters.brand);
        const queryString = params.toString();
        return api.get(`/products/${queryString ? `?${queryString}` : ''}`);
    },

    // Get product details
    getDetail: (productId: number) => api.get(`/products/${productId}/`),

    // Create product (admin/seller only)
    create: (data: {
        name: string;
        brand: string;
        category: number;
        price: number;
        description?: string;
        stock?: number;
        warranty_duration_months?: number;
        image?: File;
    }) => {
        const formData = new FormData();
        Object.entries(data).forEach(([key, value]) => {
            if (value !== undefined) {
                formData.append(key, value instanceof File ? value : String(value));
            }
        });
        return api.post('/products/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },

    // Update product
    update: (productId: number, data: Partial<{
        name: string;
        brand: string;
        category: number;
        price: number;
        description: string;
        stock: number;
        warranty_duration_months: number;
    }>) => api.patch(`/products/${productId}/`, data),

    // Delete product
    delete: (productId: number) => api.delete(`/products/${productId}/`),

    // Compare products (2-4 products)
    compare: (productIds: number[]) => api.post('/products/compare/', { product_ids: productIds }),

    // Export products as Excel
    exportExcel: () => api.get('/products/export/excel/', { responseType: 'blob' }),

    // Get user's products
    getMyProducts: () => api.get('/products/my-products/'),
};

// ----------------------------------------
// Category API Functions
// ----------------------------------------
export const categoryAPI = {
    getAll: () => api.get('/categories/'),
    getDetail: (categoryId: number) => api.get(`/categories/${categoryId}/`),
    create: (data: { name: string; parent?: number }) => api.post('/categories/', data),
    update: (categoryId: number, data: { name: string; parent?: number }) =>
        api.patch(`/categories/${categoryId}/`, data),
    delete: (categoryId: number) => api.delete(`/categories/${categoryId}/`),
};

// ----------------------------------------
// Stock Intelligence API Functions (Stok Zekası)
// ----------------------------------------
export const stockIntelligenceAPI = {
    // Get dashboard summary with critical alerts and opportunities
    getDashboardSummary: () => api.get('/stock-intelligence/'),

    // Get critical stock alerts only
    getCriticalAlerts: () => api.get('/stock-intelligence/?view=critical'),

    // Get seasonal opportunities
    getOpportunities: () => api.get('/stock-intelligence/?view=opportunities'),

    // Get all recommendations with full details
    getAllRecommendations: () => api.get('/stock-intelligence/?view=all'),
};

// ----------------------------------------
// Sales Forecast API (Satış Tahmini)
// ----------------------------------------
export const salesForecastAPI = {
    // Get dashboard summary with top forecasts
    getSummary: () => api.get('/analytics/sales-forecast/'),

    // Get forecast for specific product
    getProductForecast: (productId: number, months?: number) =>
        api.get('/analytics/sales-forecast/', { params: { product_id: productId, months } }),

    // Get forecast for category
    getCategoryForecast: (categoryId: number, months?: number) =>
        api.get('/analytics/sales-forecast/', { params: { category_id: categoryId, months } }),
};

// ----------------------------------------
// Customer Analytics API (Müşteri Değeri / CLV)
// ----------------------------------------
export const customerAnalyticsAPI = {
    // Get customer analytics summary
    getSummary: () => api.get('/analytics/customer-analytics/'),

    // Get CLV for specific customer
    getCustomerCLV: (customerId: number) =>
        api.get('/analytics/customer-analytics/', { params: { customer_id: customerId } }),

    // Get customers by segment
    getBySegment: (segment: 'vip' | 'premium' | 'standard' | 'low') =>
        api.get('/analytics/customer-analytics/', { params: { segment } }),
};

// ----------------------------------------
// Route Optimization API (Rota Optimizasyonu)
// ----------------------------------------
interface Stop {
    id: number;
    name: string;
    address: string;
    latitude: number;
    longitude: number;
    priority?: number;
}

export const routeOptimizationAPI = {
    // Optimize route for given stops
    optimizeRoute: (stops: Stop[], depot?: { latitude: number; longitude: number }, startTime?: string) =>
        api.post('/analytics/route-optimize/', { stops, depot, start_time: startTime }),

    // Get optimized route for deliveries on a specific date
    getDeliveriesRoute: (date: string) =>
        api.get('/analytics/route-optimize/', { params: { date } }),
};

// ----------------------------------------
// Marketing Automation API (Pazarlama Otomasyonu)
// ----------------------------------------
export const marketingAPI = {
    // Get campaign stats and eligible customer counts
    getStats: () => api.get('/analytics/marketing/'),

    // Run marketing campaign
    runCampaign: (campaign: 'birthday' | 'churn' | 'review' | 'welcome' | 'all', dryRun?: boolean) =>
        api.post('/analytics/marketing/', { campaign, dry_run: dryRun }),
};

// ----------------------------------------
// Dashboard Charts API (Grafikler)
// ----------------------------------------
export const chartsAPI = {
    // Get all dashboard chart data
    getAll: () => api.get('/analytics/charts/'),

    // Get specific chart type
    getSalesTrend: (months?: number) =>
        api.get('/analytics/charts/', { params: { type: 'sales', months } }),

    getDailySales: (days?: number) =>
        api.get('/analytics/charts/', { params: { type: 'daily', days } }),

    getRevenueByCategory: () =>
        api.get('/analytics/charts/', { params: { type: 'revenue' } }),

    getTopProducts: (limit?: number) =>
        api.get('/analytics/charts/', { params: { type: 'products', limit } }),

    getCustomerSegments: () =>
        api.get('/analytics/charts/', { params: { type: 'customers' } }),

    getServicesByStatus: () =>
        api.get('/analytics/charts/', { params: { type: 'services' } }),
};

// ----------------------------------------
// Audit Log API (Denetim Kayıtları)
// ----------------------------------------
export const auditLogAPI = {
    // Get recent audit logs (admin only)
    getLogs: (limit?: number) =>
        api.get('/analytics/audit-logs/', { params: { limit } }),

    // Filter by action type
    getByAction: (action: string, limit?: number) =>
        api.get('/analytics/audit-logs/', { params: { action, limit } }),

    // Filter by user
    getByUser: (userId: number, limit?: number) =>
        api.get('/analytics/audit-logs/', { params: { user_id: userId, limit } }),
};

export default api;

