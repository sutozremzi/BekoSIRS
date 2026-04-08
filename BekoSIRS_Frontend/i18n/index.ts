// i18n/index.ts — i18n configuration
import { I18n } from 'i18n-js';
import { getLocales } from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';

import tr from './tr';
import en from './en';

const LANGUAGE_KEY = 'app_language';

const i18n = new I18n({ tr, en });

// Varsayılan ayarlar
i18n.defaultLocale = 'tr';
i18n.locale = 'tr';
i18n.enableFallback = true; // Çeviri yoksa defaultLocale'e düşer

/**
 * Kaydedilmiş dil tercihini AsyncStorage'dan yükle.
 * Yoksa cihaz dilini kontrol et, o da yoksa Türkçe.
 */
export async function loadSavedLanguage(): Promise<string> {
  try {
    const saved = await AsyncStorage.getItem(LANGUAGE_KEY);
    if (saved && (saved === 'tr' || saved === 'en')) {
      i18n.locale = saved;
      return saved;
    }

    // Cihaz dilini kontrol et
    const deviceLocales = getLocales();
    const deviceLang = deviceLocales?.[0]?.languageCode;
    if (deviceLang === 'en') {
      i18n.locale = 'en';
      return 'en';
    }

    // Varsayılan: Türkçe
    i18n.locale = 'tr';
    return 'tr';
  } catch {
    i18n.locale = 'tr';
    return 'tr';
  }
}

/**
 * Dil tercihini değiştir ve AsyncStorage'a kaydet.
 */
export async function changeLanguage(lang: 'tr' | 'en'): Promise<void> {
  i18n.locale = lang;
  await AsyncStorage.setItem(LANGUAGE_KEY, lang);
}

/**
 * Çeviri helper — kısa kullanım için.
 */
export function t(key: string, options?: Record<string, any>): string {
  return i18n.t(key, options);
}

export default i18n;
