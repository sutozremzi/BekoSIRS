/**
 * @file settings.test.tsx
 * @description Ayarlar ekranı için birim testleri.
 * Şifre değiştirme, e-posta güncelleme ve çıkış yapma işlemlerini doğrular.
 */
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import SettingsScreen from '../app/(drawer)/settings';
import api from '../services';
import { Alert } from 'react-native';

// Mock Expo Router
jest.mock('expo-router', () => ({
    useRouter: () => ({
        replace: jest.fn(),
    }),
}));

// Mock API
jest.mock('../services', () => ({
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
}));

// Mock Storage
jest.mock('../storage/storage.native', () => ({
    getToken: jest.fn(),
    getRefreshToken: jest.fn(),
    clearTokens: jest.fn(),
    clearAllTokens: jest.fn().mockResolvedValue(undefined),
    deleteToken: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
    default: {
        clear: jest.fn(),
    },
}));

// Spy on Alert
jest.spyOn(Alert, 'alert');

describe('SettingsScreen Tests', () => {
    beforeEach(() => {
        jest.clearAllMocks();

        (api.get as jest.Mock).mockResolvedValue({ data: { id: 1 } });
        (api.post as jest.Mock).mockResolvedValue({ data: { success: true } });
    });

    it('renders security tab by default with logout button', async () => {
        const { getByText } = render(<SettingsScreen />);

        await waitFor(() => {
            expect(getByText('Güvenlik')).toBeTruthy();
            expect(getByText('Şifre')).toBeTruthy();
            expect(getByText('İletişim')).toBeTruthy();
            expect(getByText('Çıkış Yap')).toBeTruthy();
        });
    });

    it('switches to password tab and renders form', async () => {
        const { getByText, getByPlaceholderText } = render(<SettingsScreen />);

        fireEvent.press(getByText('Şifre'));

        await waitFor(() => {
            expect(getByText('Şifre Güncelleme')).toBeTruthy();
            expect(getByText('Hesap güvenliğinizi korumak için şifrenizi güncel tutun.')).toBeTruthy();
            expect(getByPlaceholderText('••••••••')).toBeTruthy();
            expect(getByPlaceholderText('En az 6 karakter')).toBeTruthy();
            expect(getByText('Şifreyi Güncelle')).toBeTruthy();
        });
    });

    it('handles password change validation and submit', async () => {
        const { getByText, getByPlaceholderText } = render(<SettingsScreen />);

        fireEvent.press(getByText('Şifre'));

        await waitFor(() => expect(getByText('Şifreyi Güncelle')).toBeTruthy());

        fireEvent.press(getByText('Şifreyi Güncelle'));
        expect(Alert.alert).toHaveBeenCalledWith('Eksik Bilgi', 'Lütfen tüm alanları doldurun.');

        fireEvent.changeText(getByPlaceholderText('••••••••'), 'oldPass123');
        fireEvent.changeText(getByPlaceholderText('En az 6 karakter'), 'newPass123');
        fireEvent.changeText(getByPlaceholderText('Tekrar giriniz'), 'newPass123');

        fireEvent.press(getByText('Şifreyi Güncelle'));

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/api/v1/change-password/', {
                old_password: 'oldPass123',
                new_password: 'newPass123'
            });
            expect(Alert.alert).toHaveBeenCalledWith('Başarılı', 'Güvenlik bilgileriniz güncellendi.');
        });
    });

    it('switches to email tab and handles email change', async () => {
        const { getByText, getByPlaceholderText } = render(<SettingsScreen />);

        fireEvent.press(getByText('İletişim'));

        await waitFor(() => expect(getByText('E-posta Bilgileri')).toBeTruthy());

        fireEvent.changeText(getByPlaceholderText('ornek@beko.com'), 'test@test.com');
        fireEvent.changeText(getByPlaceholderText('Doğrulama için şifreniz'), 'myPassword123');

        fireEvent.press(getByText('E-postayı Güncelle'));

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/api/v1/change-email/', {
                new_email: 'test@test.com',
                password: 'myPassword123'
            });
            expect(Alert.alert).toHaveBeenCalledWith('Başarılı', 'İletişim bilgileriniz güncellendi.');
        });
    });

    it('handles logout process', async () => {
        const { getByText } = render(<SettingsScreen />);

        await waitFor(() => expect(getByText('Oturum İşlemleri')).toBeTruthy());

        fireEvent.press(getByText('Çıkış Yap'));
    });
});
