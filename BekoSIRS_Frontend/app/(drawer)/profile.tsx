import React, { useState, useEffect, useCallback } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Platform, // 1. Platform eklendi
} from 'react-native';
import { FontAwesome } from '@expo/vector-icons';
import { useAuth } from '../../hooks/useAuth';
import { useRouter } from 'expo-router';
import api from '../../services/api';

interface UserProfile {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  role: string;
  date_joined: string;
}

const ProfileScreen = () => {
  const { authToken, logout, isCheckingAuth } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Edit form state
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');

  // Password change
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const fetchProfile = useCallback(async () => {
    try {
      const response = await api.get('/api/profile/');
      setProfile(response.data);
      setFirstName(response.data.first_name || '');
      setLastName(response.data.last_name || '');
      setEmail(response.data.email || '');
      setPhoneNumber(response.data.phone_number || '');
    } catch (error) {
      console.error('Profil yüklenemedi:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (authToken) {
      fetchProfile();
    } else {
      setLoading(false);
    }
  }, [authToken, fetchProfile]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchProfile();
  }, [fetchProfile]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updateData: any = {
        first_name: firstName,
        last_name: lastName,
        email: email,
        phone_number: phoneNumber,
      };

      // Şifre değişikliği varsa ekle
      if (showPasswordChange && newPassword) {
        if (newPassword !== confirmPassword) {
          Alert.alert('Hata', 'Yeni şifreler eşleşmiyor');
          setSaving(false);
          return;
        }
        if (newPassword.length < 6) {
          Alert.alert('Hata', 'Şifre en az 6 karakter olmalıdır');
          setSaving(false);
          return;
        }
        updateData.current_password = currentPassword;
        updateData.new_password = newPassword;
      }

      const response = await api.patch('/api/profile/', updateData);

      if (response.data.success) {
        if (Platform.OS === 'web') {
            window.alert('Profil bilgileriniz güncellendi');
        } else {
            Alert.alert('Başarılı', 'Profil bilgileriniz güncellendi');
        }
        setEditing(false);
        setShowPasswordChange(false);
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        fetchProfile();
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Güncelleme başarısız';
      if (Platform.OS === 'web') {
          window.alert(errorMsg);
      } else {
          Alert.alert('Hata', errorMsg);
      }
    } finally {
      setSaving(false);
    }
  };

  // 2. Güvenli Çıkış Fonksiyonu (Web ve Mobil Uyumlu)
  const handleLogout = () => {
    if (Platform.OS === 'web') {
      // Web tarayıcıları için window.confirm kullanımı
      const isConfirmed = window.confirm('Hesabınızdan çıkış yapmak istediğinize emin misiniz?');
      if (isConfirmed) {
        logout(); // useAuth içindeki logout fonksiyonunu çağırır
      }
    } else {
      // Mobil cihazlar için Alert.alert kullanımı
      Alert.alert(
        'Çıkış Yap',
        'Hesabınızdan çıkış yapmak istediğinize emin misiniz?',
        [
          { text: 'İptal', style: 'cancel' },
          {
            text: 'Çıkış Yap',
            style: 'destructive',
            onPress: logout,
          },
        ]
      );
    }
  };

  const cancelEdit = () => {
    setEditing(false);
    setShowPasswordChange(false);
    if (profile) {
      setFirstName(profile.first_name || '');
      setLastName(profile.last_name || '');
      setEmail(profile.email || '');
      setPhoneNumber(profile.phone_number || '');
    }
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  // Auth kontrolü yapılırken bekle
  if (isCheckingAuth) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#000000" />
      </View>
    );
  }

  // Token yoksa login'e yönlendir
  if (!authToken) {
    router.replace('/login');
    return null;
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#000000" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#000']} />
        }
      >
        {/* Profile Header */}
        <View style={styles.header}>
          <View style={styles.avatarContainer}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {(profile?.first_name?.[0] || profile?.username?.[0] || 'U').toUpperCase()}
              </Text>
            </View>
          </View>
          <Text style={styles.username}>@{profile?.username}</Text>
          <View style={styles.roleBadge}>
            <Text style={styles.roleText}>
              {profile?.role === 'customer' ? 'Müşteri' : profile?.role === 'admin' ? 'Yönetici' : 'Satıcı'}
            </Text>
          </View>
        </View>

        {/* Profile Info Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Profil Bilgileri</Text>
            {!editing ? (
              <TouchableOpacity onPress={() => setEditing(true)} style={styles.editButton}>
                <FontAwesome name="pencil" size={16} color="#000" />
                <Text style={styles.editButtonText}>Düzenle</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity onPress={cancelEdit} style={styles.cancelButton}>
                <FontAwesome name="times" size={16} color="#666" />
                <Text style={styles.cancelButtonText}>İptal</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Form Fields */}
          <View style={styles.formGroup}>
            <Text style={styles.label}>Ad</Text>
            {editing ? (
              <TextInput
                style={styles.input}
                value={firstName}
                onChangeText={setFirstName}
                placeholder="Adınız"
                placeholderTextColor="#9CA3AF"
              />
            ) : (
              <Text style={styles.value}>{profile?.first_name || '-'}</Text>
            )}
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Soyad</Text>
            {editing ? (
              <TextInput
                style={styles.input}
                value={lastName}
                onChangeText={setLastName}
                placeholder="Soyadınız"
                placeholderTextColor="#9CA3AF"
              />
            ) : (
              <Text style={styles.value}>{profile?.last_name || '-'}</Text>
            )}
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>E-posta</Text>
            {editing ? (
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                placeholder="E-posta adresiniz"
                placeholderTextColor="#9CA3AF"
                keyboardType="email-address"
                autoCapitalize="none"
              />
            ) : (
              <Text style={styles.value}>{profile?.email || '-'}</Text>
            )}
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Telefon</Text>
            {editing ? (
              <TextInput
                style={styles.input}
                value={phoneNumber}
                onChangeText={setPhoneNumber}
                placeholder="Telefon numaranız"
                placeholderTextColor="#9CA3AF"
                keyboardType="phone-pad"
              />
            ) : (
              <Text style={styles.value}>{profile?.phone_number || '-'}</Text>
            )}
          </View>

          {/* Password Change Section */}
          {editing && (
            <View style={styles.passwordSection}>
              <TouchableOpacity
                style={styles.passwordToggle}
                onPress={() => setShowPasswordChange(!showPasswordChange)}
              >
                <FontAwesome
                  name={showPasswordChange ? 'chevron-up' : 'chevron-down'}
                  size={14}
                  color="#666"
                />
                <Text style={styles.passwordToggleText}>
                  {showPasswordChange ? 'Şifre değişikliğini gizle' : 'Şifre değiştir'}
                </Text>
              </TouchableOpacity>

              {showPasswordChange && (
                <View style={styles.passwordFields}>
                  <View style={styles.formGroup}>
                    <Text style={styles.label}>Mevcut Şifre</Text>
                    <TextInput
                      style={styles.input}
                      value={currentPassword}
                      onChangeText={setCurrentPassword}
                      placeholder="Mevcut şifreniz"
                      placeholderTextColor="#9CA3AF"
                      secureTextEntry
                    />
                  </View>
                  <View style={styles.formGroup}>
                    <Text style={styles.label}>Yeni Şifre</Text>
                    <TextInput
                      style={styles.input}
                      value={newPassword}
                      onChangeText={setNewPassword}
                      placeholder="Yeni şifreniz"
                      placeholderTextColor="#9CA3AF"
                      secureTextEntry
                    />
                  </View>
                  <View style={styles.formGroup}>
                    <Text style={styles.label}>Yeni Şifre (Tekrar)</Text>
                    <TextInput
                      style={styles.input}
                      value={confirmPassword}
                      onChangeText={setConfirmPassword}
                      placeholder="Yeni şifrenizi tekrar girin"
                      placeholderTextColor="#9CA3AF"
                      secureTextEntry
                    />
                  </View>
                </View>
              )}
            </View>
          )}

          {/* Save Button */}
          {editing && (
            <TouchableOpacity
              style={[styles.saveButton, saving && styles.saveButtonDisabled]}
              onPress={handleSave}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <FontAwesome name="check" size={16} color="#fff" />
                  <Text style={styles.saveButtonText}>Kaydet</Text>
                </>
              )}
            </TouchableOpacity>
          )}
        </View>

        {/* Account Info Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Hesap Bilgileri</Text>
          <View style={styles.infoRow}>
            <FontAwesome name="user" size={16} color="#6B7280" />
            <Text style={styles.infoLabel}>Kullanıcı Adı</Text>
            <Text style={styles.infoValue}>{profile?.username}</Text>
          </View>
          <View style={styles.infoRow}>
            <FontAwesome name="calendar" size={16} color="#6B7280" />
            <Text style={styles.infoLabel}>Kayıt Tarihi</Text>
            <Text style={styles.infoValue}>
              {profile?.date_joined
                ? new Date(profile.date_joined).toLocaleDateString('tr-TR')
                : '-'}
            </Text>
          </View>
        </View>

        {/* Logout Button */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <FontAwesome name="sign-out" size={18} color="#f44336" />
          <Text style={styles.logoutButtonText}>Çıkış Yap</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  avatarContainer: {
    marginBottom: 12,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  username: {
    fontSize: 18,
    color: '#6B7280',
    marginBottom: 8,
  },
  roleBadge: {
    backgroundColor: '#E5E7EB',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  roleText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
  },
  editButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
  },
  editButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#000',
  },
  cancelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  cancelButtonText: {
    fontSize: 14,
    color: '#666',
  },
  formGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
    marginBottom: 6,
    textTransform: 'uppercase',
  },
  value: {
    fontSize: 16,
    color: '#111827',
  },
  input: {
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: '#111827',
  },
  passwordSection: {
    marginTop: 8,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  passwordToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  passwordToggleText: {
    fontSize: 14,
    color: '#666',
  },
  passwordFields: {
    gap: 4,
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#000000',
    paddingVertical: 14,
    borderRadius: 12,
    marginTop: 8,
  },
  saveButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  infoLabel: {
    fontSize: 14,
    color: '#6B7280',
    marginLeft: 12,
    flex: 1,
  },
  infoValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#111827',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#fff',
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f44336',
  },
  logoutButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#f44336',
  },
});

export default ProfileScreen;