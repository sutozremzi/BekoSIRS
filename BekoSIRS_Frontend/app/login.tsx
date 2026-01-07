import React, { useState, useEffect } from 'react';
import {
  View,
  TextInput,
  StyleSheet,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuth } from '../hooks/useAuth';
import { useBiometric } from '../hooks/useBiometric';
import { saveTokens } from '../storage/storage.native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const LoginScreen = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login, loading } = useAuth();
  const {
    isAvailable: biometricAvailable,
    isEnabled: biometricEnabled,
    displayName: biometricName,
    loading: biometricLoading,
    authenticateWithBiometric,
    checkIfEnabled
  } = useBiometric();

  // Check biometric status on mount
  useEffect(() => {
    checkIfEnabled();
  }, []);

  const handleLogin = async () => {
    await login(username, password);
  };

  const handleBiometricLogin = async () => {
    const result = await authenticateWithBiometric();

    if (result.success && result.accessToken && result.refreshToken) {
      // Save tokens and navigate
      await saveTokens(result.accessToken, result.refreshToken);
      await AsyncStorage.setItem('user_role', 'customer');
      router.replace('/' as any);
    } else if (result.error && result.error !== 'cancelled') {
      // Error already shown in hook via Alert
    }
  };

  const isLoading = loading || biometricLoading;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Header Section */}
          <View style={styles.header}>
            <View style={styles.logoBadge}>
              <Text style={styles.logoText}>BEKO</Text>
            </View>
            <Text style={styles.title}>Hoş Geldiniz</Text>
            <Text style={styles.subtitle}>
              Ürün yönetim sistemine güvenli erişim sağlayın
            </Text>
          </View>

          {/* Login Card */}
          <View style={styles.card}>
            {/* Biometric Login Button - Show if enabled */}
            {biometricAvailable && biometricEnabled && (
              <>
                <TouchableOpacity
                  style={styles.biometricButton}
                  onPress={handleBiometricLogin}
                  disabled={isLoading}
                  activeOpacity={0.8}
                >
                  {biometricLoading ? (
                    <ActivityIndicator color="#000000" />
                  ) : (
                    <>
                      <Text style={styles.biometricIcon}>
                        {biometricName === 'Face ID' || biometricName === 'Yüz Tanıma' ? '👤' : '👆'}
                      </Text>
                      <Text style={styles.biometricButtonText}>
                        {biometricName} ile Giriş
                      </Text>
                    </>
                  )}
                </TouchableOpacity>

                <View style={styles.divider}>
                  <View style={styles.line} />
                  <Text style={styles.dividerText}>veya şifre ile</Text>
                  <View style={styles.line} />
                </View>
              </>
            )}

            <View style={styles.inputSection}>
              <Text style={styles.label}>Kullanıcı Adı</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  placeholder="Kullanıcı adınızı girin"
                  value={username}
                  onChangeText={setUsername}
                  autoCapitalize="none"
                  autoCorrect={false}
                  placeholderTextColor="#9CA3AF"
                  editable={!isLoading}
                />
              </View>
            </View>

            <View style={styles.inputSection}>
              <Text style={styles.label}>Şifre</Text>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.input}
                  placeholder="••••••••"
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                  placeholderTextColor="#9CA3AF"
                  editable={!isLoading}
                />
                <TouchableOpacity
                  onPress={() => setShowPassword(!showPassword)}
                  style={styles.iconButton}
                >
                  <Text style={styles.iconText}>
                    {showPassword ? '👁️' : '👁️‍🗨️'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            <TouchableOpacity
              style={styles.forgotPassContainer}
              onPress={() => router.push('/forgot-password' as any)}
            >
              <Text style={styles.forgotPassText}>Şifremi Unuttum</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.primaryButton, (isLoading || !username || !password) && styles.buttonDisabled]}
              onPress={handleLogin}
              disabled={isLoading || !username || !password}
              activeOpacity={0.8}
            >
              {loading ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.buttonText}>Giriş Yap</Text>
              )}
            </TouchableOpacity>

            <View style={styles.divider}>
              <View style={styles.line} />
              <Text style={styles.dividerText}>veya</Text>
              <View style={styles.line} />
            </View>

            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={() => router.push('/register')}
              disabled={isLoading}
            >
              <Text style={styles.secondaryButtonText}>Yeni Hesap Oluştur</Text>
            </TouchableOpacity>
          </View>

          {/* Footer Info */}
          <View style={styles.footer}>
            <Text style={styles.footerCopyright}>
              © 2025 Beko Global. Tüm hakları saklıdır.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 30,
    paddingVertical: 40,
  },
  header: {
    alignItems: 'center',
    marginBottom: 45,
  },
  logoBadge: {
    backgroundColor: '#000000',
    paddingHorizontal: 25,
    paddingVertical: 10,
    borderRadius: 12,
    marginBottom: 20,
  },
  logoText: {
    color: '#FFFFFF',
    fontSize: 28,
    fontWeight: '900',
    letterSpacing: 2,
  },
  title: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#111827',
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 8,
    textAlign: 'center',
  },
  card: {
    backgroundColor: '#FFFFFF',
  },
  // Biometric button styles
  biometricButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F3F4F6',
    height: 58,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#2563EB',
    marginBottom: 20,
  },
  biometricIcon: {
    fontSize: 24,
    marginRight: 10,
  },
  biometricButtonText: {
    color: '#2563EB',
    fontSize: 16,
    fontWeight: '700',
  },
  inputSection: {
    marginBottom: 20,
  },
  label: {
    fontSize: 13,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 14,
    paddingHorizontal: 16,
  },
  input: {
    flex: 1,
    height: 54,
    fontSize: 15,
    color: '#111827',
    fontWeight: '500',
  },
  iconButton: {
    padding: 10,
  },
  iconText: {
    fontSize: 18,
  },
  forgotPassContainer: {
    alignSelf: 'flex-end',
    marginBottom: 25,
  },
  forgotPassText: {
    fontSize: 14,
    color: '#000000',
    fontWeight: '700',
  },
  primaryButton: {
    backgroundColor: '#000000',
    height: 58,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  buttonDisabled: {
    backgroundColor: '#E5E7EB',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '800',
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 25,
  },
  line: {
    flex: 1,
    height: 1,
    backgroundColor: '#F3F4F6',
  },
  dividerText: {
    marginHorizontal: 15,
    color: '#9CA3AF',
    fontSize: 12,
    fontWeight: '600',
  },
  secondaryButton: {
    height: 58,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: '#E5E7EB',
    justifyContent: 'center',
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#111827',
    fontSize: 15,
    fontWeight: '700',
  },
  footer: {
    marginTop: 'auto',
    paddingTop: 40,
    alignItems: 'center',
  },
  footerCopyright: {
    fontSize: 12,
    color: '#9CA3AF',
    fontWeight: '500',
  },
});

export default LoginScreen;