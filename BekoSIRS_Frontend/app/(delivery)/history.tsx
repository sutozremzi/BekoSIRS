import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ActivityIndicator,
    StatusBar,
    ScrollView,
    RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import api from '../../services/api';

interface Delivery {
    id: number;
    order_number: string;
    customer_name: string;
    address: string;
    customer_address?: string;
    status: string;
    delivery_order: number;
    product_name: string;
}

export default function DeliveryHistory() {
    const [deliveries, setDeliveries] = useState<Delivery[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const fetchHistory = async () => {
        try {
            const res = await api.get('/api/v1/delivery-person/my_route/');
            const data = res.data;
            const allDeliveries = Array.isArray(data) ? data : (Array.isArray(data?.deliveries) ? data.deliveries : []);
            
            // Sadece tamamlanan (DELIVERED) olanları filtrele
            const deliveredItems = allDeliveries.filter((d: Delivery) => d.status === 'DELIVERED');
            setDeliveries(deliveredItems);
        } catch (error) {
            console.error('Failed to fetch history:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, []);

    const onRefresh = () => {
        setRefreshing(true);
        fetchHistory();
    };

    if (loading) {
        return (
            <SafeAreaView style={styles.container}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#005696" />
                    <Text style={styles.loadingText}>Geçmiş yükleniyor...</Text>
                </View>
            </SafeAreaView>
        );
    }

    return (
        <View style={styles.container}>
            <StatusBar barStyle="dark-content" />

            {/* Header */}
            <SafeAreaView style={styles.header} edges={['top']}>
                <TouchableOpacity
                    style={styles.backButton}
                    onPress={() => router.back()}
                >
                    <Ionicons name="arrow-back" size={24} color="#1e293b" />
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Teslimat Geçmişi</Text>
                <View style={{ width: 40 }} /> {/* Layout balance */}
            </SafeAreaView>

            {/* List */}
            <ScrollView 
                style={styles.scrollView} 
                contentContainerStyle={styles.scrollContent}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#005696']} />}
            >
                <Text style={styles.sectionTitle}>Tamamlanan Teslimatlar</Text>

                {deliveries.length === 0 ? (
                    <View style={styles.emptyState}>
                        <Ionicons name="checkmark-done-circle-outline" size={64} color="#cbd5e1" />
                        <Text style={styles.emptyText}>Henüz biten teslimat yok</Text>
                    </View>
                ) : (
                    deliveries.map((delivery, index) => (
                        <View key={delivery.id} style={styles.historyCard}>
                            <View style={styles.historyCardHeader}>
                                <Text style={styles.customerName}>{delivery.customer_name || 'Müşteri'}</Text>
                                <View style={styles.statusBadge}>
                                    <Ionicons name="checkmark-circle" size={14} color="#16a34a" />
                                    <Text style={styles.statusText}>Teslim Edildi</Text>
                                </View>
                            </View>
                            <View style={styles.productRow}>
                                <Ionicons name="cube-outline" size={16} color="#64748b" />
                                <Text style={styles.productText} numberOfLines={1}>{delivery.product_name || 'Ürün bilgisi yok'}</Text>
                            </View>
                            <View style={styles.addressRow}>
                                <Ionicons name="location-outline" size={16} color="#64748b" />
                                <Text style={styles.addressText} numberOfLines={2}>{delivery.address || delivery.customer_address || 'Adres belirtilmemiş'}</Text>
                            </View>
                        </View>
                    ))
                )}

                <View style={{ height: 100 }} />
            </ScrollView>

        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F5F5F5',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loadingText: {
        marginTop: 12,
        color: '#64748b',
        fontSize: 16,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingBottom: 12,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#f1f5f9',
    },
    backButton: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: '#f1f5f9',
        justifyContent: 'center',
        alignItems: 'center',
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: '#1e293b',
    },
    scrollView: {
        flex: 1,
    },
    scrollContent: {
        padding: 16,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: '#1e293b',
        marginBottom: 16,
    },
    emptyState: {
        alignItems: 'center',
        paddingVertical: 48,
    },
    emptyText: {
        marginTop: 16,
        fontSize: 16,
        color: '#94a3b8',
    },
    historyCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 1,
        borderLeftWidth: 4,
        borderLeftColor: '#16a34a',
    },
    historyCardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    customerName: {
        fontSize: 15,
        fontWeight: '600',
        color: '#1e293b',
        flex: 1,
    },
    statusBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#dcfce7',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
        gap: 4,
    },
    statusText: {
        fontSize: 10,
        fontWeight: '700',
        color: '#16a34a',
    },
    productRow: {
        flexDirection: 'row',
        gap: 6,
        alignItems: 'center',
        marginBottom: 8,
    },
    productText: {
        flex: 1,
        fontSize: 13,
        color: '#334155',
        fontWeight: '500',
    },
    addressRow: {
        flexDirection: 'row',
        gap: 6,
        alignItems: 'flex-start',
    },
    addressText: {
        flex: 1,
        fontSize: 13,
        color: '#64748b',
        lineHeight: 18,
    },
});
