import React, { useState } from 'react';
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
import { useLanguage } from '../context/LanguageContext';
import { t } from '../i18n';

const LoginScreen = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    const { login, loading: authLoading } = useAuth();
    const { language } = useLanguage();

    const handleLogin = async () => {
        await login(username, password);
    };

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
                                    editable={!authLoading}
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
                                    editable={!authLoading}
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
                            style={[styles.primaryButton, (authLoading || !username || !password) && styles.buttonDisabled]}
                            onPress={handleLogin}
                            disabled={authLoading || !username || !password}
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
                            disabled={authLoading}
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
