import { Drawer } from 'expo-router/drawer';
import { FontAwesome } from '@expo/vector-icons';
import { View, Text, StyleSheet } from 'react-native';
import { DrawerContentScrollView, DrawerItemList } from '@react-navigation/drawer';

// Orijinal tema renkleri
const THEME = {
  primary: '#000000',      // Kurumsal siyah
  secondary: '#111827',    // Koyu gri
  accent: '#374151',       // Orta gri
  background: '#FFFFFF',   // Beyaz
  text: '#111827',
  textLight: '#6B7280',
  border: '#E5E7EB',
};

function CustomDrawerContent(props: any) {
  return (
    <DrawerContentScrollView {...props} style={{ backgroundColor: THEME.background }}>
      <View style={styles.header}>
        <View style={styles.logoContainer}>
          <Text style={styles.logoText}>BEKO</Text>
        </View>
        <Text style={styles.brandName}>BekoSIRS</Text>
        <Text style={styles.tagline}>Akıllı Envanter Sistemi</Text>
      </View>
      <View style={styles.divider} />
      <DrawerItemList {...props} />
      <View style={styles.footer}>
        <Text style={styles.footerText}>© 2025 Beko Global</Text>
      </View>
    </DrawerContentScrollView>
  );
}

export default function DrawerLayout() {
  return (
    <Drawer
      drawerContent={(props) => <CustomDrawerContent {...props} />}
      screenOptions={{
        headerStyle: { backgroundColor: THEME.primary },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: { fontWeight: 'bold', fontSize: 18 },
        drawerActiveTintColor: THEME.primary,
        drawerInactiveTintColor: THEME.accent,
        drawerActiveBackgroundColor: '#F3F4F6',
        drawerLabelStyle: { marginLeft: -10, fontSize: 15, fontWeight: '600' },
        drawerItemStyle: { borderRadius: 12, marginHorizontal: 8, marginVertical: 2 },
      }}
    >
      <Drawer.Screen
        name="index"
        options={{
          drawerLabel: 'Ana Sayfa',
          title: 'Ürünler',
          drawerIcon: ({ color, size }) => <FontAwesome name="home" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="my-products"
        options={{
          drawerLabel: 'Ürünlerim',
          title: 'Ürünlerim',
          drawerIcon: ({ color, size }) => <FontAwesome name="cube" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="wishlist"
        options={{
          drawerLabel: 'İstek Listem',
          title: 'İstek Listem',
          drawerIcon: ({ color, size }) => <FontAwesome name="heart" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="recommendations"
        options={{
          drawerLabel: 'Size Özel Öneriler',
          title: 'Öneriler',
          drawerIcon: ({ color, size }) => <FontAwesome name="lightbulb-o" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="service-requests"
        options={{
          drawerLabel: 'Servis Taleplerim',
          title: 'Servis Talepleri',
          drawerIcon: ({ color, size }) => <FontAwesome name="wrench" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="notifications"
        options={{
          drawerLabel: 'Bildirimler',
          title: 'Bildirimler',
          drawerIcon: ({ color, size }) => <FontAwesome name="bell" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="settings"
        options={{
          drawerLabel: 'Ayarlar',
          title: 'Ayarlar',
          drawerIcon: ({ color, size }) => <FontAwesome name="cog" size={size} color={color} />,
        }}
      />
      <Drawer.Screen
        name="profile"
        options={{
          drawerLabel: 'Hesabım',
          title: 'Profilim',
          drawerIcon: ({ color, size }) => <FontAwesome name="user" size={size} color={color} />,
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
    backgroundColor: THEME.primary,
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
    marginBottom: 8,
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
