// hooks/useBiometric.ts
import { useState } from 'react';
import { Alert } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import api from '../services/api';

const BIOMETRIC_REFRESH_TOKEN = 'biometric_refresh_token';

export const useBiometric = () => {
    const [loading, setLoading] = useState(false);

    // ------------------------------------------------------------------ //
    //  Eski tek-frame akışı (geriye dönük uyumluluk)
    // ------------------------------------------------------------------ //

    /** Yüzü sisteme kaydeder (tek fotoğraf, liveness atlanır). */
    const enableBiometric = async (
        imageUri: string,
        refreshToken?: string,
    ): Promise<boolean> => {
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('face_image', {
                uri: imageUri,
                name: 'face_register.jpg',
                type: 'image/jpeg',
            } as any);

            if (refreshToken) {
                formData.append('refresh_token', refreshToken);
            }

            await api.post('/api/v1/biometric/enable/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            if (refreshToken) {
                await SecureStore.setItemAsync(BIOMETRIC_REFRESH_TOKEN, refreshToken);
            }

            Alert.alert('Başarılı', 'Yüzünüz sisteme güvenle kaydedildi (Özellik Vektörü olarak).');
            return true;
        } catch (error: any) {
            const msg =
                error.response?.data?.error ||
                'Yüz kaydedilemedi. Lütfen net bir fotoğraf çekin.';
            Alert.alert('Hata', msg);
            return false;
        } finally {
            setLoading(false);
        }
    };

    /** Tek fotoğraf ile Face ID girişi (liveness kontrolü olmadan). */
    const loginWithFace = async (
        username: string,
        imageUri: string,
    ): Promise<{
        success: boolean;
        accessToken?: string;
        refreshToken?: string;
        userId?: number;
        error?: string;
    }> => {
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('face_image', {
                uri: imageUri,
                name: 'face_login.jpg',
                type: 'image/jpeg',
            } as any);

            const verifyResponse = await api.post(
                '/api/v1/biometric/login/',
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } },
            );

            if (!verifyResponse.data.success) {
                return {
                    success: false,
                    error: verifyResponse.data.error || 'Yüz eşleşmedi.',
                };
            }

            const { access, refresh } = verifyResponse.data.tokens;
            const userId = verifyResponse.data.user_id;

            await SecureStore.setItemAsync(BIOMETRIC_REFRESH_TOKEN, refresh);

            return { success: true, accessToken: access, refreshToken: refresh, userId };
        } catch (error: any) {
            const errorMsg =
                error.response?.data?.error || error.response?.data?.detail;
            return {
                success: false,
                error: errorMsg || 'Giriş işlemi başarısız oldu.',
            };
        } finally {
            setLoading(false);
        }
    };

    // ------------------------------------------------------------------ //
    //  Yeni 3-frame Aktif Liveness akışı (Issue #30)
    // ------------------------------------------------------------------ //

    /**
     * Standalone liveness kontrolü — 3 frame gönderir, backend analiz eder.
     *
     * Backend'deki frame subtraction + entropi analizi:
     *   • Gerçek insan: 3D perspektif + arka plan hareketi → yüksek fark
     *   • Sahte (foto/tablet): düz yüzey → düşük fark, düşük entropi
     *
     * @returns { is_live, score (0-1), reason }
     */
    const performLivenessCheck = async (
        frameLeftUri: string,
        frameCenterUri: string,
        frameRightUri: string,
    ): Promise<{ is_live: boolean; score: number; reason: string }> => {
        try {
            const formData = new FormData();
            formData.append('frame_left', {
                uri: frameLeftUri,
                name: 'frame_left.jpg',
                type: 'image/jpeg',
            } as any);
            formData.append('frame_center', {
                uri: frameCenterUri,
                name: 'frame_center.jpg',
                type: 'image/jpeg',
            } as any);
            formData.append('frame_right', {
                uri: frameRightUri,
                name: 'frame_right.jpg',
                type: 'image/jpeg',
            } as any);

            const response = await api.post(
                '/api/v1/biometric/liveness-check/',
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } },
            );

            return {
                is_live: response.data.is_live ?? false,
                score:   response.data.score   ?? 0,
                reason:  response.data.reason  ?? '',
            };
        } catch (error: any) {
            const reason =
                error.response?.data?.reason ||
                error.response?.data?.error ||
                'Canlılık kontrolü başarısız oldu.';
            return { is_live: false, score: 0, reason };
        }
    };

    /**
     * 3 frame ile Face ID girişi (Liveness → Kimlik doğrulama).
     *
     * İş akışı:
     *   1) /biometric/liveness-check/ → 3 frame analiz edilir (frame subtraction)
     *   2) Canlı ise /biometric/login/ → merkez frame + 3 frame ile kimlik doğrulama
     *
     * @param username        Kullanıcı adı
     * @param frameLeftUri    Sol açı frame  (yaw ≈ -25°)
     * @param frameCenterUri  Merkez frame   (yaw ≈  0°)
     * @param frameRightUri   Sağ açı frame  (yaw ≈ +25°)
     */
    const loginWithFace3Frame = async (
        username: string,
        frameLeftUri: string,
        frameCenterUri: string,
        frameRightUri: string,
    ): Promise<{
        success: boolean;
        accessToken?: string;
        refreshToken?: string;
        userId?: number;
        error?: string;
    }> => {
        setLoading(true);
        try {
            // ── Adım 1: Liveness ───────────────────────────────────────────
            const liveness = await performLivenessCheck(
                frameLeftUri,
                frameCenterUri,
                frameRightUri,
            );

            if (!liveness.is_live) {
                return {
                    success: false,
                    error: `Canlılık doğrulaması başarısız (skor: ${(liveness.score * 100).toFixed(0)}%). Lütfen başınızı yavaşça çevirerek tekrar deneyin.`,
                };
            }

            // ── Adım 2: Yüz eşleştirme ─────────────────────────────────────
            const formData = new FormData();
            formData.append('username', username);
            // Ana resim: merkez frame
            formData.append('face_image', {
                uri: frameCenterUri,
                name: 'face_login.jpg',
                type: 'image/jpeg',
            } as any);
            // Opsiyonel: backend de yeniden kontrol edebilsin diye 3 frame
            formData.append('frame_left', {
                uri: frameLeftUri,
                name: 'frame_left.jpg',
                type: 'image/jpeg',
            } as any);
            formData.append('frame_center', {
                uri: frameCenterUri,
                name: 'frame_center.jpg',
                type: 'image/jpeg',
            } as any);
            formData.append('frame_right', {
                uri: frameRightUri,
                name: 'frame_right.jpg',
                type: 'image/jpeg',
            } as any);

            const verifyResponse = await api.post(
                '/api/v1/biometric/login/',
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } },
            );

            if (!verifyResponse.data.success) {
                return {
                    success: false,
                    error: verifyResponse.data.error || 'Yüz eşleşmedi.',
                };
            }

            const { access, refresh } = verifyResponse.data.tokens;
            const userId = verifyResponse.data.user_id;

            await SecureStore.setItemAsync(BIOMETRIC_REFRESH_TOKEN, refresh);

            return { success: true, accessToken: access, refreshToken: refresh, userId };
        } catch (error: any) {
            const errorMsg =
                error.response?.data?.error ||
                error.response?.data?.detail;
            return {
                success: false,
                error: errorMsg || 'Giriş işlemi başarısız oldu.',
            };
        } finally {
            setLoading(false);
        }
    };

    // ------------------------------------------------------------------ //
    //  Ortak
    // ------------------------------------------------------------------ //

    const disableBiometric = async (): Promise<boolean> => {
        setLoading(true);
        try {
            await api.post('/api/v1/biometric/disable/');
            await SecureStore.deleteItemAsync(BIOMETRIC_REFRESH_TOKEN);
            Alert.alert('Başarılı', 'Yüz kaydınız başarıyla silindi.');
            return true;
        } catch (error) {
            return false;
        } finally {
            setLoading(false);
        }
    };

    /**
     * Video tabanlı liveness + Face ID girişi.
     *
     * İş akışı:
     *   1) /biometric/liveness-check-video/ → kısa video analiz edilir (frame subtraction)
     *   2) Canlı ise /biometric/login/ → selfie frame ile kimlik doğrulama
     *
     * @param videoUri    Expo Camera'nın recordAsync ile döndüreceği video URI'si
     * @param selfieUri   Kimlik doğrulama için merkez frame (JPEG)
     * @param username    Kullanıcı adı
     */
    const loginWithFaceVideo = async (
        username: string,
        videoUri: string,
        selfieUri: string,
    ): Promise<{
        success: boolean;
        accessToken?: string;
        refreshToken?: string;
        userId?: number;
        error?: string;
    }> => {
        setLoading(true);
        try {
            // ── Adım 1: Video liveness kontrolü ───────────────────────────
            const liveFormData = new FormData();
            liveFormData.append('video', {
                uri: videoUri,
                name: 'liveness.mp4',
                type: 'video/mp4',
            } as any);

            let livenessOk = false;
            let livenessError = '';
            try {
                const liveRes = await api.post(
                    '/api/v1/biometric/liveness-check-video/',
                    liveFormData,
                    { headers: { 'Content-Type': 'multipart/form-data' } },
                );
                livenessOk = liveRes.data.is_live ?? false;
                if (!livenessOk) {
                    livenessError =
                        liveRes.data.reason ||
                        'Canlılık doğrulanamadı. Başınızı belirgin şekilde çevirerek tekrar deneyin.';
                }
            } catch (e: any) {
                livenessError =
                    e.response?.data?.reason ||
                    e.response?.data?.error ||
                    'Canlılık kontrolü başarısız oldu.';
            }

            if (!livenessOk) {
                return { success: false, error: livenessError };
            }

            // ── Adım 2: Yüz eşleştirme (selfie ile) ───────────────────────
            const loginFormData = new FormData();
            loginFormData.append('username', username);
            loginFormData.append('face_image', {
                uri: selfieUri,
                name: 'face_login.jpg',
                type: 'image/jpeg',
            } as any);

            const verifyResponse = await api.post(
                '/api/v1/biometric/login/',
                loginFormData,
                { headers: { 'Content-Type': 'multipart/form-data' } },
            );

            if (!verifyResponse.data.success) {
                return {
                    success: false,
                    error: verifyResponse.data.error || 'Yüz eşleşmedi.',
                };
            }

            const { access, refresh } = verifyResponse.data.tokens;
            const userId = verifyResponse.data.user_id;
            await SecureStore.setItemAsync(BIOMETRIC_REFRESH_TOKEN, refresh);

            return { success: true, accessToken: access, refreshToken: refresh, userId };
        } catch (error: any) {
            return {
                success: false,
                error: error.response?.data?.error || error.response?.data?.detail || 'Giriş başarısız.',
            };
        } finally {
            setLoading(false);
        }
    };

    /**
     * Multi-frame liveness + Face ID girişi.
     *
     * Frontend N tane JPEG URI gönderir (5sn boyunca her 500ms'de bir çekilen),
     * backend ardışık frame subtraction ile liveness analizi yapar.
     * Video codec sorunu YOK — sadece JPEG dosyaları.
     *
     * @param username   Kullanıcı adı
     * @param frameUris  Ardışık fotoğraf URI listesi (en az 6, en fazla 12)
     * @param selfieUri  Kimlik doğrulama için merkez selfie
     */
    const loginWithFaceMulti = async (
        username: string,
        frameUris: string[],
        selfieUri: string,
    ): Promise<{
        success: boolean;
        accessToken?: string;
        refreshToken?: string;
        userId?: number;
        error?: string;
    }> => {
        setLoading(true);
        try {
            // ── Adım 1: Multi-frame liveness ───────────────────────────────
            const liveFormData = new FormData();
            frameUris.forEach((uri, idx) => {
                liveFormData.append(`frame_${idx}`, {
                    uri,
                    name: `frame_${idx}.jpg`,
                    type: 'image/jpeg',
                } as any);
            });

            let livenessOk = false;
            let livenessError = '';
            try {
                const liveRes = await api.post(
                    '/api/v1/biometric/liveness-check-multi/',
                    liveFormData,
                    { headers: { 'Content-Type': 'multipart/form-data' } },
                );
                livenessOk = liveRes.data.is_live ?? false;
                livenessError = liveRes.data.reason || 'Canlılık doğrulanamadı.';
            } catch (e: any) {
                livenessError =
                    e.response?.data?.reason ||
                    e.response?.data?.error ||
                    `Canlılık isteği başarısız (${e.message}).`;
            }

            if (!livenessOk) {
                return { success: false, error: livenessError };
            }

            // ── Adım 2: Yüz eşleştirme ─────────────────────────────────────
            const loginFormData = new FormData();
            loginFormData.append('username', username);
            loginFormData.append('face_image', {
                uri: selfieUri,
                name: 'face_login.jpg',
                type: 'image/jpeg',
            } as any);

            const verifyResponse = await api.post(
                '/api/v1/biometric/login/',
                loginFormData,
                { headers: { 'Content-Type': 'multipart/form-data' } },
            );

            if (!verifyResponse.data.success) {
                return { success: false, error: verifyResponse.data.error || 'Yüz eşleşmedi.' };
            }

            const { access, refresh } = verifyResponse.data.tokens;
            const userId = verifyResponse.data.user_id;
            await SecureStore.setItemAsync(BIOMETRIC_REFRESH_TOKEN, refresh);

            return { success: true, accessToken: access, refreshToken: refresh, userId };
        } catch (error: any) {
            return {
                success: false,
                error: error.response?.data?.error || 'Giriş başarısız.',
            };
        } finally {
            setLoading(false);
        }
    };

    // ------------------------------------------------------------------ //
    //  Ayrıştırılmış 2-Aşamalı Akış
    //  Aşama 1: checkLivenessMulti  → sadece liveness kontrol
    //  Aşama 2: verifyFaceOnly      → sadece selfie ile yüz eşleştirme
    // ------------------------------------------------------------------ //

    /** Sadece liveness kontrolü yapar, yüz eşleştirme yapmaz. */
    const checkLivenessMulti = async (
        frameUris: string[],
    ): Promise<{ isLive: boolean; reason: string }> => {
        setLoading(true);
        try {
            const formData = new FormData();
            frameUris.forEach((uri, idx) => {
                formData.append(`frame_${idx}`, {
                    uri,
                    name: `frame_${idx}.jpg`,
                    type: 'image/jpeg',
                } as any);
            });

            const res = await api.post(
                '/api/v1/biometric/liveness-check-multi/',
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } },
            );
            return {
                isLive: res.data.is_live ?? false,
                reason: res.data.reason ?? '',
            };
        } catch (e: any) {
            return {
                isLive: false,
                reason: e.response?.data?.reason
                    || e.response?.data?.error
                    || `Liveness isteği başarısız (${e.message}).`,
            };
        } finally {
            setLoading(false);
        }
    };

    /** Sadece selfie ile yüz eşleştirmesi yapar (liveness zaten geçti). */
    const verifyFaceOnly = async (
        username: string,
        selfieUri: string,
    ): Promise<{
        success: boolean;
        accessToken?: string;
        refreshToken?: string;
        userId?: number;
        error?: string;
    }> => {
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('face_image', {
                uri: selfieUri,
                name: 'face_login.jpg',
                type: 'image/jpeg',
            } as any);

            const res = await api.post(
                '/api/v1/biometric/login/',
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } },
            );

            if (!res.data.success) {
                return { success: false, error: res.data.error || 'Yüz eşleşmedi.' };
            }

            const { access, refresh } = res.data.tokens;
            const userId = res.data.user_id;
            await SecureStore.setItemAsync(BIOMETRIC_REFRESH_TOKEN, refresh);

            return { success: true, accessToken: access, refreshToken: refresh, userId };
        } catch (error: any) {
            return {
                success: false,
                error: error.response?.data?.error || 'Yüz doğrulama başarısız.',
            };
        } finally {
            setLoading(false);
        }
    };

    // ------------------------------------------------------------------ //
    //  Birleşik Tek-Adımlı Akış — Liveness + Face Verification atomik
    //  Zafiyet giderimi: Aynı frame'lerle hem liveness hem yüz eşleştirme
    // ------------------------------------------------------------------ //

    /**
     * Tek adımda liveness + face verification yapar.
     *
     * Tüm frame'ler + username tek istekte gönderilir.
     * Backend aynı frame'lerden hem liveness kontrolü hem de
     * yüz eşleştirmesi yapar → ara adımda farklı yüz gösterme zafiyeti kapanır.
     *
     * @param username   Kullanıcı adı
     * @param frameUris  Ardışık fotoğraf URI listesi (en az 3)
     */
    const loginWithLivenessUnified = async (
        username: string,
        frameUris: string[],
    ): Promise<{
        success: boolean;
        accessToken?: string;
        refreshToken?: string;
        userId?: number;
        error?: string;
    }> => {
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('username', username);
            frameUris.forEach((uri, idx) => {
                formData.append(`frame_${idx}`, {
                    uri,
                    name: `frame_${idx}.jpg`,
                    type: 'image/jpeg',
                } as any);
            });

            const res = await api.post(
                '/api/v1/biometric/login-with-liveness/',
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } },
            );

            if (!res.data.success) {
                return {
                    success: false,
                    error: res.data.error || 'Giriş başarısız.',
                };
            }

            const { access, refresh } = res.data.tokens;
            const userId = res.data.user_id;
            await SecureStore.setItemAsync(BIOMETRIC_REFRESH_TOKEN, refresh);

            return { success: true, accessToken: access, refreshToken: refresh, userId };
        } catch (error: any) {
            const errorMsg =
                error.response?.data?.error ||
                error.response?.data?.detail ||
                `Giriş başarısız (${error.message}).`;
            return { success: false, error: errorMsg };
        } finally {
            setLoading(false);
        }
    };

    return {
        loading,
        enableBiometric,
        disableBiometric,
        loginWithFace,
        loginWithFace3Frame,
        loginWithFaceVideo,
        loginWithFaceMulti,
        checkLivenessMulti,
        verifyFaceOnly,
        loginWithLivenessUnified,
        performLivenessCheck,
    };
};
