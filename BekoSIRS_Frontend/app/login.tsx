import React, { useState, useRef } from 'react';
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
    Alert,
    Modal,
    Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuth } from '../hooks/useAuth';
import { useBiometric } from '../hooks/useBiometric';
import { saveTokens } from '../storage/storage.native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useLanguage } from '../context/LanguageContext';
import { t } from '../i18n';

const { width: SCREEN_W } = Dimensions.get('window');
const RECORD_SECONDS = 5; // Kayıt süresi (saniye)

const LoginScreen = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    // Camera & liveness state
    const [showCamera, setShowCamera] = useState(false);
    const [permission, requestPermission] = useCameraPermissions();
    const cameraRef = useRef<any>(null);
    const [isRecording, setIsRecording] = useState(false);
    const [countdown, setCountdown] = useState(RECORD_SECONDS);
    const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const capturedFramesRef = useRef<string[]>([]);
    const frameIntervalRef  = useRef<ReturnType<typeof setInterval> | null>(null);

    const { login, loading: authLoading } = useAuth();
    const { loginWithLivenessUnified, checkBiometricStatusPublic, loading: bioLoading } = useBiometric();
    const { language } = useLanguage();

    const handleLogin = async () => {
        await login(username, password);
    };

    /** Face ID butonu: izin al, kamerayı aç. */
    const handleBiometricPress = async () => {
        let currentUsername = username;
        if (!currentUsername) {
            const SecureStore = require('expo-secure-store');
            const savedUsername = await SecureStore.getItemAsync('lastLoginUsername');
            if (savedUsername) {
                currentUsername = savedUsername;
                setUsername(currentUsername);
            } else {
                Alert.alert(t('common.error'), t('login.faceIdInfo'));
                return;
            }
        }

        // Check if biometric is enabled on backend before opening camera
        const statusObj = await checkBiometricStatusPublic(currentUsername);
        if (statusObj.lockedOut) {
            const minutes = Math.ceil(statusObj.remaining / 60);
            Alert.alert(
                t('common.error'),
                `Çok fazla başarısız deneme nedeniyle yüz tanıma geçici olarak kilitlendi. Lütfen şifrenizle giriş yapın veya ${minutes} dakika sonra tekrar deneyin. / Face recognition has been locked due to too many failed attempts. Please log in with your password or try again in ${minutes} minutes.`
            );
            return;
        }
        if (!statusObj.enabled) {
            Alert.alert(
                t('common.error'),
                'Yüz tanıma bu hesap için etkin değil. Lütfen önce ayarlardan yüz tanımayı etkinleştirin. / Face recognition is not enabled for this account. Please enable it in settings first.'
            );
            return;
        }

        if (!permission?.granted) {
            const result = await requestPermission();
            if (!result.granted) {
                Alert.alert(t('common.error'), t('login.cameraPermission'));
                return;
            }
        }

        setCountdown(RECORD_SECONDS);
        setIsRecording(false);
        setShowCamera(true);
    };

    /**
     * Tek adımlı akış: frame çek → hepsini username ile gönder
     * Backend aynı frame'lerden hem liveness hem yüz eşleştirme yapar.
     * Zafiyet giderildi: Ayrı selfie adımı yok.
     */
    const startRecording = async () => {
        if (!cameraRef.current || isRecording) return;
        setIsRecording(true);
        setCountdown(RECORD_SECONDS);
        capturedFramesRef.current = [];

        // Countdown timer
        let remaining = RECORD_SECONDS;
        countdownRef.current = setInterval(() => {
            remaining -= 1;
            setCountdown(remaining);
            if (remaining <= 0) clearInterval(countdownRef.current!);
        }, 1000);

        // Her 600ms'de bir frame çek
        const INTERVAL_MS   = 600;
        const totalDuration = RECORD_SECONDS * 1000;

        frameIntervalRef.current = setInterval(async () => {
            if (!cameraRef.current) return;
            try {
                const photo = await cameraRef.current.takePictureAsync({
                    base64: false,
                    quality: 0.75,
                    skipProcessing: true,
                });
                capturedFramesRef.current.push(photo.uri);
            } catch { /* tek frame hatasını yoksay */ }
        }, INTERVAL_MS);

        // 5sn sonra durdur ve hepsini birden gönder
        await new Promise(r => setTimeout(r, totalDuration));
        clearInterval(frameIntervalRef.current!);
        clearInterval(countdownRef.current!);
        setIsRecording(false);
        setShowCamera(false);

        const frames = capturedFramesRef.current;

        if (frames.length < 3) {
            Alert.alert('Hata', 'Yeterli frame yakalanamadı. Lütfen tekrar deneyin.');
            return;
        }

        // Tek istekte hem liveness hem yüz doğrulama
        const result = await loginWithLivenessUnified(username, frames);
        if (result.success && result.accessToken && result.refreshToken) {
            await saveTokens(result.accessToken, result.refreshToken);
            await AsyncStorage.setItem('userRole', 'customer');
            router.replace('/(drawer)' as any);
        } else {
            Alert.alert(t('login.loginFailed'), result.error || 'Giriş başarısız.');
        }
    };

    /** Kamerayı kapat ve sıfırla. */
    const closeCameraModal = () => {
        clearInterval(frameIntervalRef.current!);
        clearInterval(countdownRef.current!);
        setIsRecording(false);
        setShowCamera(false);
    };


    const isLoading = authLoading || bioLoading;

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
                    <View style={styles.header}>
                        <View style={styles.logoBadge}>
                            <Text style={styles.logoText}>BEKO</Text>
                        </View>
                        <Text style={styles.title}>{t('login.welcome')}</Text>
                        <Text style={styles.subtitle}>
                            {t('login.subtitle')}
                        </Text>
                    </View>

                    <View style={styles.card}>
                        <TouchableOpacity
                            style={styles.biometricButton}
                            onPress={handleBiometricPress}
                            disabled={isLoading}
                            activeOpacity={0.8}
                        >
                            {bioLoading ? (
                                <ActivityIndicator color="#2563EB" />
                            ) : (
                                <>
                                    <Text style={styles.biometricIcon}>👤</Text>
                                    <Text style={styles.biometricButtonText}>
                                        {t('login.faceId')}
                                    </Text>
                                </>
                            )}
                        </TouchableOpacity>

                        <View style={styles.divider}>
                            <View style={styles.line} />
                            <Text style={styles.dividerText}>{t('login.orPassword')}</Text>
                            <View style={styles.line} />
                        </View>

                        <View style={styles.inputSection}>
                            <Text style={styles.label}>{t('login.username')}</Text>
                            <View style={styles.inputWrapper}>
                                <TextInput
                                    style={styles.input}
                                    placeholder={t('login.usernamePlaceholder')}
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
                            <Text style={styles.label}>{t('login.password')}</Text>
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
                            <Text style={styles.forgotPassText}>{t('login.forgotPassword')}</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={[styles.primaryButton, (isLoading || !username || !password) && styles.buttonDisabled]}
                            onPress={handleLogin}
                            disabled={isLoading || !username || !password}
                            activeOpacity={0.8}
                        >
                            {authLoading ? (
                                <ActivityIndicator color="#FFFFFF" />
                            ) : (
                                <Text style={styles.buttonText}>{t('login.login')}</Text>
                            )}
                        </TouchableOpacity>

                        <View style={styles.divider}>
                            <View style={styles.line} />
                            <Text style={styles.dividerText}>{t('common.or')}</Text>
                            <View style={styles.line} />
                        </View>

                        <TouchableOpacity
                            style={styles.secondaryButton}
                            onPress={() => router.push('/register' as any)}
                            disabled={isLoading}
                        >
                            <Text style={styles.secondaryButtonText}>{t('login.createAccount')}</Text>
                        </TouchableOpacity>
                    </View>

                    <View style={styles.footer}>
                        <Text style={styles.footerCopyright}>
                            {t('login.copyright')}
                        </Text>
                    </View>
                </ScrollView>
            </KeyboardAvoidingView>

            {/* Kamera Modali — TEK ADIMLI (Liveness + Doğrulama aynı anda) */}
            {showCamera && (
                <Modal animationType="slide" transparent={false} visible={showCamera}>
                    <View style={styles.cameraContainer}>
                        <CameraView
                            style={styles.camera}
                            facing="front"
                            ref={cameraRef}
                        >
                            {/* Kapat butonu — kayıt sırasında gizle */}
                            {!isRecording && (
                                <TouchableOpacity
                                    style={styles.closeCameraTopBtn}
                                    onPress={closeCameraModal}
                                >
                                    <Text style={styles.closeCameraTopText}>✕</Text>
                                </TouchableOpacity>
                            )}

                            {/* ── Liveness + Doğrulama (Tek Adım) ── */}
                            <View style={styles.cameraOverlay}>
                                <View style={[
                                    styles.faceOutline,
                                    { borderColor: isRecording ? '#EF4444' : '#10B981' }
                                ]} />
                                {isRecording ? (
                                    <View style={styles.countdownContainer}>
                                        <Text style={styles.countdownNumber}>{countdown}</Text>
                                        <Text style={styles.countdownLabel}>● KAYIT</Text>
                                        <Text style={styles.cameraSubText}>
                                            Başınızı yavaşça sola-sağa çevirin
                                        </Text>
                                    </View>
                                ) : (
                                    <Text style={styles.cameraText}>
                                        Butona basın ve başınızı{'\n'}yavaşça sola-sağa çevirin
                                    </Text>
                                )}
                            </View>
                            {!isRecording && (
                                <View style={styles.cameraControls}>
                                    <View style={{ width: 60 }} />
                                    <TouchableOpacity
                                        style={styles.captureButton}
                                        onPress={startRecording}
                                    >
                                        <View style={[styles.captureButtonInner, { backgroundColor: '#EF4444' }]} />
                                    </TouchableOpacity>
                                    <View style={{ width: 60 }} />
                                </View>
                            )}
                        </CameraView>

                        {/* Analiz yükleniyor */}
                        {bioLoading && (
                            <View style={styles.loadingOverlay}>
                                <ActivityIndicator size="large" color="#fff" />
                                <Text style={styles.loadingText}>
                                    Canlılık ve kimlik doğrulanıyor...
                                </Text>
                            </View>
                        )}
                    </View>
                </Modal>
            )}
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    cameraContainer: { flex: 1, backgroundColor: 'black' },
    camera: { flex: 1 },

    // Kapat butonu (sol üst)
    closeCameraTopBtn: {
        position: 'absolute',
        top: 50,
        left: 20,
        zIndex: 10,
        backgroundColor: 'rgba(0,0,0,0.5)',
        borderRadius: 20,
        paddingHorizontal: 14,
        paddingVertical: 6,
    },
    closeCameraTopText: {
        color: 'white',
        fontSize: 18,
        fontWeight: 'bold',
    },


    cameraOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.35)',
        justifyContent: 'center',
        alignItems: 'center',
        paddingTop: 80,
    },
    faceOutline: {
        width: 220,
        height: 300,
        borderWidth: 3,
        borderRadius: 130,
        borderStyle: 'dashed',
    },
    cameraText: {
        color: 'white',
        fontSize: 18,
        marginTop: 24,
        fontWeight: 'bold',
        textAlign: 'center',
        paddingHorizontal: 30,
        textShadowColor: 'rgba(0,0,0,0.8)',
        textShadowOffset: { width: 0, height: 1 },
        textShadowRadius: 4,
    },
    cameraSubText: {
        color: 'rgba(255,255,255,0.7)',
        fontSize: 13,
        marginTop: 8,
        fontWeight: '500',
    },
    countdownContainer: {
        alignItems: 'center',
        marginTop: 20,
    },
    countdownNumber: {
        color: '#EF4444',
        fontSize: 72,
        fontWeight: 'bold',
        lineHeight: 80,
    },
    countdownLabel: {
        color: '#EF4444',
        fontSize: 14,
        fontWeight: '700',
        letterSpacing: 3,
        marginTop: 4,
    },
    cameraControls: {
        height: 130,
        backgroundColor: 'rgba(0,0,0,0.85)',
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'center',
        paddingBottom: 24,
    },
    captureButton: {
        width: 76,
        height: 76,
        borderRadius: 38,
        backgroundColor: 'rgba(255, 255, 255, 0.25)',
        borderWidth: 3,
        borderColor: 'white',
        justifyContent: 'center',
        alignItems: 'center',
    },
    captureButtonInner: {
        width: 62,
        height: 62,
        borderRadius: 31,
        backgroundColor: 'white',
    },

    // Liveness yükleniyor katmanı
    loadingOverlay: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: 'rgba(0,0,0,0.75)',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 16,
    },
    loadingText: {
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
        marginTop: 12,
    },


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
    }
});

export default LoginScreen;
