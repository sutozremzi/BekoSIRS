// context/LanguageContext.tsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { loadSavedLanguage, changeLanguage as changeI18nLanguage } from '../i18n';

type LanguageContextType = {
  language: string;
  changeLanguage: (lang: 'tr' | 'en') => Promise<void>;
  isReady: boolean;
};

const LanguageContext = createContext<LanguageContextType>({
  language: 'tr',
  changeLanguage: async () => {},
  isReady: false,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState('tr');
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    loadSavedLanguage().then((lang) => {
      setLanguage(lang);
      setIsReady(true);
    });
  }, []);

  const changeLanguage = useCallback(async (lang: 'tr' | 'en') => {
    await changeI18nLanguage(lang);
    setLanguage(lang);
  }, []);

  return (
    <LanguageContext.Provider value={{ language, changeLanguage, isReady }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
