import { Drawer } from 'expo-router/drawer';
import { Tabs } from 'expo-router';
import { FontAwesome } from '@expo/vector-icons';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { DrawerContentScrollView, DrawerItemList } from '@react-navigation/drawer';
import { useNavigation } from '@react-navigation/native';
import { DrawerActions } from '@react-navigation/native';
import { useLanguage } from '../../context/LanguageContext';
import { t } from '../../i18n';

// Beko tema renkleri
const THEME = {
  primary: '#E31E24',      // Beko kırmızısı
  primaryDark: '#C01820',  // Koyu kırmızı
  black: '#000000',        // Siyah
  secondary: '#111827',    // Koyu gri
  accent: '#374151',       // Orta gri
  background: '#FFFFFF',   // Beyaz
  text: '#111827',
  textLight: '#6B7280',
  gray: '#9CA3AF',         // Gri
  lightGray: '#E5E7EB',    // Açık gri
  border: '#E5E7EB',
  white: '#FFFFFF',
};

function CustomDrawerContent(props: any) {
  const { language } = useLanguage();
  return (
    <DrawerContentScrollView {...props} style={{ backgroundColor: THEME.background }}>
      <View style={styles.header}>
        <View style={styles.logoContainer}>
          <Text style={styles.logoText}>BEKO</Text>
        </View>
        <Text style={styles.brandName}>BekoSIRS</Text>
        <Text style={styles.tagline}>{t('nav.tagline')}</Text>
      </View>
      <View style={styles.divider} />
      <DrawerItemList {...props} />
      <View style={styles.footer}>
        <Text style={styles.footerText}>© 2025 Beko Global</Text>
      </View>
    </DrawerContentScrollView>
  );
}

// DrawerToggleButton component for headers
function DrawerToggleButton() {
  const navigation = useNavigation();

  return (
    <Pressable
      onPress={() => navigation.dispatch(DrawerActions.toggleDrawer())}
      style={({ pressed }) => ({
        marginLeft: 15,
        opacity: pressed ? 0.5 : 1,
      })}
    >
      <FontAwesome name="bars" size={24} color="#FFFFFF" />
    </Pressable>
  );
}

export default function DrawerLayout() {
  const { language } = useLanguage();
  return (
    <Drawer
      key={language}
      drawerContent={(props) => <CustomDrawerContent {...props} />}
      screenOptions={{
        headerStyle: { backgroundColor: THEME.black },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: { fontWeight: 'bold', fontSize: 18 },
        drawerActiveTintColor: THEME.primary,
        drawerInactiveTintColor: THEME.accent,
        drawerActiveBackgroundColor: '#F3F4F6',
        drawerLabelStyle: { marginLeft: -10, fontSize: 16, fontWeight: '600' },
        drawerItemStyle: { borderRadius: 12, marginHorizontal: 12, marginVertical: 8, paddingVertical: 4 },
        headerLeft: () => <DrawerToggleButton />,
      }}
    >
      {/* Tabs Group - Ana ekran (Bottom tabs ile) */}
      <Drawer.Screen
        name="(tabs)"
        options={{
          drawerLabel: t('nav.home'),
          title: 'BekoSIRS',
          drawerIcon: ({ color, size }) => <FontAwesome name="home" size={size} color={color} />,
        }}
      />

      {/* Diğer sayfalar */}
      <Drawer.Screen
        name="recommendations"
        options={{
          drawerLabel: t('nav.recommendations'),
          title: t('nav.recommendationsShort'),
          drawerIcon: ({ color, size }) => <FontAwesome name="lightbulb-o" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="service-requests"
        options={{
          drawerLabel: t('nav.serviceRequests'),
          title: t('nav.serviceRequestsShort'),
          drawerIcon: ({ color, size }) => <FontAwesome name="wrench" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="payments"
        options={{
          drawerLabel: t('nav.payments'),
          title: t('nav.payments'),
          drawerIcon: ({ color, size }) => <FontAwesome name="credit-card" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="notifications"
        options={{
          drawerLabel: t('nav.notifications'),
          title: t('nav.notifications'),
          drawerIcon: ({ color, size }) => <FontAwesome name="bell" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="settings"
        options={{
          drawerLabel: t('nav.settings'),
          title: t('nav.settings'),
          drawerIcon: ({ color, size }) => <FontAwesome name="cog" size={size} color={color} />,
        }}
      />
    </Drawer>
  );
}

const styles = StyleSheet.create({
  header: {
    padding: 24,
    alignItems: 'center',
    backgroundColor: THEME.background,
  },
  logoContainer: {
    backgroundColor: THEME.black,
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 10,
    marginBottom: 12,
  },
  logoText: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 2,
  },
  brandName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: THEME.text,
  },
  tagline: {
    fontSize: 12,
    color: THEME.textLight,
    marginTop: 4,
  },
  divider: {
    height: 1,
    backgroundColor: THEME.border,
    marginHorizontal: 20,
    marginTop: 8,
    marginBottom: 16,
  },
  footer: {
    padding: 20,
    alignItems: 'center',
    marginTop: 20,
  },
  footerText: {
    fontSize: 11,
    color: THEME.textLight,
  },
});


