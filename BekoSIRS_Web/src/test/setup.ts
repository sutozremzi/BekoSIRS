// src/test/setup.ts
// Global test setup for Vitest + React Testing Library

import '@testing-library/jest-dom';

const translations: Record<string, string> = {
    'sidebar.dashboard': 'Dashboard',
    'sidebar.analytics': 'Analitikler',
    'sidebar.installments': 'Taksitler',
    'sidebar.products': 'Urunler',
    'sidebar.categories': 'Kategoriler',
    'sidebar.serviceRequests': 'Servis Talepleri',
    'sidebar.reviews': 'Degerlendirmeler',
    'sidebar.groups': 'Gruplar',
    'sidebar.users': 'Kullanicilar',
    'sidebar.customers': 'Musteri Yonetimi',
    'sidebar.assignments': 'Urun Atamalari',
    'sidebar.depots': 'Depolar',
    'sidebar.notifications': 'Bildirimler',
    'sidebar.adminPanel': 'Admin Panel',
    'sidebar.sellerPanel': 'Satici Paneli',
    'sidebar.admin': 'Admin',
    'sidebar.seller': 'Satici',
    'sidebar.manager': 'Yonetici',
    'sidebar.authUser': 'Yetkili Kullanici',
    'sidebar.logout': 'Cikis Yap',
    'sidebar.logoutConfirm': 'Cikis yapmak istediginizden emin misiniz?',
    'navbar.language': 'Dil Secimi',
    'auth.plcUsername': 'Kullan\u0131c\u0131 ad\u0131n\u0131z',
    'auth.lblUsername': 'Kullan\u0131c\u0131 Ad\u0131',
    'auth.lblPassword': '\u015eifre',
    'auth.btnLogin': 'Sisteme Giri\u015f Yap',
    'auth.loginTitle': 'Y\u00f6netici Giri\u015fi',
    'auth.loginSubtitle': 'Hesab\u0131n\u0131za giri\u015f yap\u0131n',
    'auth.heroTitle': 'BekoSIRS',
    'auth.heroDesc': 'AkÄ±llÄ± envanter sistemi',
    'auth.feature1': 'Envanter',
    'auth.feature2': 'Analitik',
    'auth.feature3': 'Teslimat',
    'notFound.title': 'Sayfa Bulunamad\u0131',
    'notFound.desc': 'Arad\u0131\u011f\u0131n\u0131z sayfa bulunamad\u0131.',
    'notFound.btnBack': 'Geri D\u00f6n',
    'notFound.btnDashboard': "Dashboard'a Git",
    'installments.btnCancel': 'Planı İptal Et',
    'installments.btnApprove': 'Onayla',
    'installments.daysOverdue': '{{days}} gün gecikmiş',
    'installments.daysLeft': '{{days}} gün kaldı',
    'installments.todayDue': 'Bugün',
    'installments.btnEdit': 'Düzenle',
    'installments.btnSave': 'Kaydet',
    'installments.btnCancelEdit': 'İptal',
    'installments.btnConfirmCancel': 'Evet, İptal Et',
    'installments.titleCancelPlan': 'Taksit Planini Iptal Et',
};

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key: string, params?: Record<string, any>) => {
            const fallback = params?.defaultValue ?? key;
            let value = translations[key] ?? fallback;
            if (params) {
                Object.entries(params).forEach(([paramKey, paramValue]) => {
                    value = String(value).replaceAll(`{{${paramKey}}}`, String(paramValue));
                });
            }
            return value;
        },
        i18n: {
            language: 'tr',
            changeLanguage: vi.fn(),
        },
    }),
    initReactI18next: {
        type: '3rdParty',
        init: vi.fn(),
    },
}));

// Mock localStorage with actual storage
const localStorageStore: Record<string, string> = {};
const localStorageMock = {
    getItem: (key: string) => localStorageStore[key] || null,
    setItem: (key: string, value: string) => { localStorageStore[key] = value; },
    removeItem: (key: string) => { delete localStorageStore[key]; },
    clear: () => { Object.keys(localStorageStore).forEach(key => delete localStorageStore[key]); },
};
Object.defineProperty(global, 'localStorage', { value: localStorageMock });

// Mock fetch for API calls
global.fetch = vi.fn();

// Reset mocks before each test
beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
});
