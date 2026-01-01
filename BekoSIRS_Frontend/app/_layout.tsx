// app/_layout.tsx
import React, { useEffect, useState } from 'react';
import { Stack, useSegments, useRouter } from 'expo-router';
import { View, ActivityIndicator } from 'react-native';
import { isAuthenticated } from '../storage/storage'; // .native uzantısı yok

export default function RootLayout() {
  const segments = useSegments();
  const router = useRouter();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const checkAuthAndNavigate = async () => {
      // 1. Güncel durumu kontrol et
      const hasToken = await isAuthenticated();
      
      // 2. Hangi sayfadayız?
      const inAuthPage = segments[0] === 'login' || segments[0] === 'register';

      // 3. Yönlendirme Mantığı
      if (!hasToken && !inAuthPage) {
        // Token yoksa ve içerideyse -> Login'e at
        router.replace('/login');
      } else if (hasToken && inAuthPage) {
        // Token varsa ve Login'deyse -> İçeri al
        router.replace('/(drawer)');
      }

      setIsReady(true);
    };

    checkAuthAndNavigate();
  }, [segments]); // Sayfa her değiştiğinde bu kontrol çalışır

  if (!isReady) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' }}>
        <ActivityIndicator size="large" color="#000000" />
      </View>
    );
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(drawer)" options={{ headerShown: false }} />
      <Stack.Screen name="login" options={{ headerShown: false }} />
      <Stack.Screen name="register" options={{ headerShown: false }} />
      <Stack.Screen
        name="product/[id]"
        options={{
          headerShown: true,
          headerTitle: 'Ürün Detayı',
          headerStyle: { backgroundColor: '#000000' },
          headerTintColor: '#FFFFFF',
          headerBackTitle: 'Geri',
          presentation: 'card',
        }}
      />
    </Stack>
  );
}