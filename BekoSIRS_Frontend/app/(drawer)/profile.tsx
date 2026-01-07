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
  Modal,
  Platform,
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
  address?: string;
  address_city?: string;
}

const TRNC_CITIES = [
  'Lefkoşa',
  'Gazimağusa',
  'Girne',
  'Güzelyurt',
  'İskele',
  'Lefke'
];

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

  // Address form state
  const [city, setCity] = useState('');
  const [district, setDistrict] = useState(''); // Mahalle/Bölge
  const [street, setStreet] = useState('');     // Cadde/Sokak
  const [buildingNo, setBuildingNo] = useState(''); // Kapı No
  const [addressNote, setAddressNote] = useState(''); // Tarif (Hastane karşısı vb.)

  const [showCityModal, setShowCityModal] = useState(false);

  // Password change
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Adres stringini parçalara ayırma (basit mantık)
  const parseAddress = (fullAddress: string) => {
    if (!fullAddress) return;

    // Format: "Mahalle, Cadde, No:12 - Not: Tarif"
    // Bu basit bir parsing, mükemmel olmayabilir ama iş görür
    const parts = fullAddress.split(' - Not: ');
    setAddressNote(parts[1] || ''); // Varsa notu al

    const mainParts = parts[0].split(', ');
    if (mainParts.length >= 3) {
      setDistrict(mainParts[0] || '');
      setStreet(mainParts[1] || '');
      setBuildingNo(mainParts[2]?.replace('No:', '') || '');
    } else {
      // Format uymuyorsa düz metin olarak bölgeye koy
      setDistrict(parts[0]);
    }
  };

  const fetchProfile = useCallback(async () => {
    try {
      const response = await api.get('/api/profile/');
      setProfile(response.data);
      setFirstName(response.data.first_name || '');
      setLastName(response.data.last_name || '');
      setEmail(response.data.email || '');
      setPhoneNumber(response.data.phone_number || '');

      setCity(response.data.address_city || '');
      parseAddress(response.data.address || ''); // Mevcut adresi form alanlarına dağıt

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

  useEffect(() => {
    if (!authToken && !isCheckingAuth) {
      router.replace('/login');
    }
  }, [authToken, isCheckingAuth]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchProfile();
  }, [fetchProfile]);

  const handleSave = async () => {
    setSaving(true);
    try {
      // Adresi birleştir
      let fullAddress = '';
      if (district || street || buildingNo) {
        fullAddress = `${district}, ${street}, No:${buildingNo}`;
        if (addressNote) {
          fullAddress += ` - Not: ${addressNote}`;
        }
      }

      const updateData: any = {
        first_name: firstName,
        last_name: lastName,
        email: email,
        phone_number: phoneNumber,
        address_city: city,
        address: fullAddress,
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
        Alert.alert('Başarılı', 'Profil bilgileriniz güncellendi');
        setEditing(false);
        setShowPasswordChange(false);
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        fetchProfile();
      }
    } catch (error: any) {
      Alert.alert('Hata', error.response?.data?.error || 'Güncelleme başarısız');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
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
  };

  const cancelEdit = () => {
    setEditing(false);
    setShowPasswordChange(false);
    if (profile) {
      setFirstName(profile.first_name || '');
      setLastName(profile.last_name || '');
      setEmail(profile.email || '');
      setPhoneNumber(profile.phone_number || '');
      setCity(profile.address_city || '');
      parseAddress(profile.address || '');
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

  // Token yoksa login'e yönlendirilecek, boş dön
  if (!authToken) {
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

          {/* New Address Section */}
          <View style={styles.divider} />
          <Text style={styles.sectionTitle}>Adres Bilgileri</Text>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Şehir</Text>
            {editing ? (
              <TouchableOpacity
                style={styles.input}
                onPress={() => setShowCityModal(true)}
              >
                <Text style={{ color: city ? '#000' : '#9CA3AF' }}>
                  {city || 'Şehir Seçiniz'}
                </Text>
                <FontAwesome name="chevron-down" size={12} color="#666" style={{ position: 'absolute', right: 15, top: 15 }} />
              </TouchableOpacity>
            ) : (
              <Text style={styles.value}>{profile?.address_city || '-'}</Text>
            )}
          </View>

          {editing ? (
            <>
              <View style={styles.row}>
                <View style={[styles.formGroup, { flex: 1, marginRight: 10 }]}>
                  <Text style={styles.label}>Bölge / Mahalle</Text>
                  <TextInput
                    style={styles.input}
                    value={district}
                    onChangeText={setDistrict}
                    placeholder="Örn: Ortaköy"
                    placeholderTextColor="#9CA3AF"
                  />
                </View>
                <View style={[styles.formGroup, { width: 100 }]}>
                  <Text style={styles.label}>Kapı No</Text>
                  <TextInput
                    style={styles.input}
                    value={buildingNo}
                    onChangeText={setBuildingNo}
                    placeholder="No"
                    placeholderTextColor="#9CA3AF"
                  />
                </View>
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.label}>Cadde / Sokak</Text>
                <TextInput
                  style={styles.input}
                  value={street}
                  onChangeText={setStreet}
                  placeholder="Örn: Atatürk Caddesi"
                  placeholderTextColor="#9CA3AF"
                />
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.label}>Adres Tarifi / Not</Text>
                <TextInput
                  style={[styles.input, { height: 80, textAlignVertical: 'top' }]}
                  value={addressNote}
                  onChangeText={setAddressNote}
                  placeholder="Örn: Devlet hastanesi karşısı, 2. kat"
                  placeholderTextColor="#9CA3AF"
                  multiline
                />
              </View>
            </>
          ) : (
            <View style={styles.formGroup}>
              <Text style={styles.label}>Açık Adres</Text>
              <Text style={styles.value}>{profile?.address || '-'}</Text>
            </View>
          )}

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

      {/* City Selection Modal */}
      <Modal
        visible={showCityModal}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowCityModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Şehir Seçiniz</Text>
              <TouchableOpacity onPress={() => setShowCityModal(false)}>
                <FontAwesome name="close" size={20} color="#666" />
              </TouchableOpacity>
            </View>
            <ScrollView style={{ maxHeight: 300 }}>
              {TRNC_CITIES.map((c) => (
                <TouchableOpacity
                  key={c}
                  style={styles.cityOption}
                  onPress={() => {
                    setCity(c);
                    setShowCityModal(false);
                  }}
                >
                  <Text style={[
                    styles.cityOptionText,
                    city === c && { fontWeight: 'bold', color: '#000' }
                  ]}>
                    {c}
                  </Text>
                  {city === c && <FontAwesome name="check" size={16} color="#000" />}
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>

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
  row: {
    flexDirection: 'row',
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
  divider: {
    height: 1,
    backgroundColor: '#E5E7EB',
    marginVertical: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#111827',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  cityOption: {
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cityOptionText: {
    fontSize: 16,
    color: '#333',
  },
});

export default ProfileScreen;
