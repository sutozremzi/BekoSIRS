import { Tabs } from 'expo-router';
import { FontAwesome } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useLanguage } from '../../../context/LanguageContext';
import { t } from '../../../i18n';

const THEME = {
    primary: '#E31E24',      // Beko kırmızısı
    black: '#000000',
    gray: '#9CA3AF',
    lightGray: '#E5E7EB',
    white: '#FFFFFF',
};

export default function TabsLayout() {
    const insets = useSafeAreaInsets();
    const { language } = useLanguage();

    return (
        <Tabs
            key={language}
            screenOptions={{
                headerShown: false,
                tabBarActiveTintColor: THEME.primary,
                tabBarInactiveTintColor: THEME.gray,
                tabBarStyle: {
                    backgroundColor: THEME.white,
                    borderTopWidth: 1,
                    borderTopColor: THEME.lightGray,
                    height: 60 + insets.bottom,
                    paddingBottom: 8 + insets.bottom,
                    paddingTop: 8,
                    elevation: 10,
                    shadowColor: '#000',
                    shadowOffset: { width: 0, height: -2 },
                    shadowOpacity: 0.1,
                    shadowRadius: 4,
                },
                tabBarLabelStyle: {
                    fontSize: 12,
                    fontWeight: '600',
                },
            }}
        >
            {/* 1. Tab - Ana Sayfa (Ürünler Listesi) */}
            <Tabs.Screen
                name="index"
                options={{
                    tabBarLabel: t('nav.home'),
                    tabBarIcon: ({ color, size }) => <FontAwesome name="home" size={size} color={color} />,
                }}
            />

            {/* 3. Tab - Favoriler (Yıldız) */}
            <Tabs.Screen
                name="wishlist"
                options={{
                    tabBarLabel: t('nav.favorites'),
                    tabBarIcon: ({ color, size }) => <FontAwesome name="star" size={size} color={color} />,
                }}
            />

            {/* 4. Tab - Ürünlerim (Satıcının atadığı ürünler) */}
            <Tabs.Screen
                name="my-products"
                options={{
                    tabBarLabel: t('nav.myProducts'),
                    tabBarIcon: ({ color, size }) => <FontAwesome name="shopping-bag" size={size} color={color} />,
                }}
            />

            {/* 5. Tab - Profil (Hesabım) */}
            <Tabs.Screen
                name="profile"
                options={{
                    tabBarLabel: t('nav.myAccount'),
                    tabBarIcon: ({ color, size }) => <FontAwesome name="user" size={size} color={color} />,
                }}
            />
        </Tabs>
    );
}
