import React, { createContext, useState, useEffect, ReactNode } from 'react';
import api from '../services/api';
import { router } from 'expo-router';
import { saveToken, getToken, deleteToken } from '../storage/storage.native';

interface AuthContextType {
  authToken: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

export const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadToken = async () => {
      const token = await getToken(); // Artık platformu kendi biliyor
      if (token) {
        setAuthToken(token);
      }
      setIsLoading(false);
    };
    loadToken();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await api.post('/api/v1/token/', { username, password });
      const { access } = response.data;
      setAuthToken(access);
      await saveToken(access); // Artık platformu kendi biliyor
      router.replace('/(drawer)/profile');
    } catch (e) {
      console.error('Login failed', e);
      alert('Giriş başarısız. Lütfen bilgilerinizi kontrol edin.');
    }
  };

  const logout = async () => {
    setAuthToken(null);
    await deleteToken(); // Artık platformu kendi biliyor
  };

  return (
    <AuthContext.Provider value={{ authToken, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider> // Doğrusu bu
  );
};