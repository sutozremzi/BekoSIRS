// src/pages/LoginPage.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from './LoginPage';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Wrapper for React Router
const renderWithRouter = (component: React.ReactNode) => {
    return render(
        <BrowserRouter>
            {component}
        </BrowserRouter>
    );
};

describe('LoginPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
    });

    it('renders login form correctly', () => {
        renderWithRouter(<LoginPage />);

        expect(screen.getByPlaceholderText('Kullanıcı adınız')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
        expect(screen.getByText('Sisteme Giriş Yap')).toBeInTheDocument();
        expect(screen.getByText('Yönetici Girişi')).toBeInTheDocument();
    });

    it('shows login button disabled when fields are empty', () => {
        renderWithRouter(<LoginPage />);

        const loginButton = screen.getByRole('button', { name: /sisteme giriş yap/i });
        expect(loginButton).toBeDisabled();
    });

    it('enables login button when both fields have values', async () => {
        const user = userEvent.setup();
        renderWithRouter(<LoginPage />);

        const usernameInput = screen.getByPlaceholderText('Kullanıcı adınız');
        const passwordInput = screen.getByPlaceholderText('••••••••');

        await user.type(usernameInput, 'admin');
        await user.type(passwordInput, 'password123');

        const loginButton = screen.getByRole('button', { name: /sisteme giriş yap/i });
        expect(loginButton).not.toBeDisabled();
    });

    it('shows error message on failed login', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: false,
            json: async () => ({ detail: 'Kullanıcı adı veya şifre hatalı' }),
        });

        const user = userEvent.setup();
        renderWithRouter(<LoginPage />);

        await user.type(screen.getByPlaceholderText('Kullanıcı adınız'), 'wronguser');
        await user.type(screen.getByPlaceholderText('••••••••'), 'wrongpass');
        await user.click(screen.getByRole('button', { name: /sisteme giriş yap/i }));

        await waitFor(() => {
            expect(screen.getByText('Kullanıcı adı veya şifre hatalı')).toBeInTheDocument();
        });
    });

    it('stores tokens on successful login', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                access: 'test-access-token',
                refresh: 'test-refresh-token',
                role: 'admin',
            }),
        });

        const user = userEvent.setup();
        renderWithRouter(<LoginPage />);

        await user.type(screen.getByPlaceholderText('Kullanıcı adınız'), 'admin');
        await user.type(screen.getByPlaceholderText('••••••••'), 'password123');
        await user.click(screen.getByRole('button', { name: /sisteme giriş yap/i }));

        await waitFor(() => {
            expect(localStorage.getItem('access')).toBe('test-access-token');
            expect(localStorage.getItem('refresh')).toBe('test-refresh-token');
            expect(localStorage.getItem('user_role')).toBe('admin');
        });
    });

    it('toggles password visibility', async () => {
        const user = userEvent.setup();
        renderWithRouter(<LoginPage />);

        const passwordInput = screen.getByPlaceholderText('••••••••');
        expect(passwordInput).toHaveAttribute('type', 'password');

        // Find and click the toggle button (there's an eye icon)
        const toggleButtons = screen.getAllByRole('button');
        const toggleButton = toggleButtons.find(btn =>
            btn.querySelector('svg') && !btn.textContent?.includes('Giriş')
        );

        if (toggleButton) {
            await user.click(toggleButton);
            expect(passwordInput).toHaveAttribute('type', 'text');
        }
    });

    it('clears old session data on page load', () => {
        localStorage.setItem('access', 'old-token');
        localStorage.setItem('refresh', 'old-refresh');
        localStorage.setItem('user_role', 'old-role');

        renderWithRouter(<LoginPage />);

        expect(localStorage.getItem('access')).toBeNull();
        expect(localStorage.getItem('refresh')).toBeNull();
        expect(localStorage.getItem('user_role')).toBeNull();
    });
});
