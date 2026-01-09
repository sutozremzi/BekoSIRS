import React, { useState, useEffect, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    FlatList,
    TouchableOpacity,
    RefreshControl,
    ActivityIndicator,
    Alert,
    Modal,
} from 'react-native';
import { FontAwesome } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { installmentAPI } from '../../services/api';

// Theme
const THEME = {
    primary: '#000000',
    secondary: '#111827',
    accent: '#374151',
    background: '#F9FAFB',
    card: '#FFFFFF',
    text: '#111827',
    textLight: '#6B7280',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    border: '#E5E7EB',
};

interface Installment {
    id: number;
    installment_number: number;
    amount: string;
    due_date: string;
    payment_date: string | null;
    status: string;
    status_display: string;
    is_overdue: boolean;
    days_until_due: number;
}

interface InstallmentPlan {
    id: number;
    product_name: string;
    total_amount: string;
    down_payment: string;
    installment_count: number;
    start_date: string;
    status: string;
    status_display: string;
    remaining_amount: string;
    paid_amount: string;
    progress_percentage: number;
    installments?: Installment[];
}

export default function InstallmentsScreen() {
    const router = useRouter();
    const [plans, setPlans] = useState<InstallmentPlan[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [selectedPlan, setSelectedPlan] = useState<InstallmentPlan | null>(null);
    const [installments, setInstallments] = useState<Installment[]>([]);
    const [detailLoading, setDetailLoading] = useState(false);
    const [confirmModalVisible, setConfirmModalVisible] = useState(false);
    const [selectedInstallment, setSelectedInstallment] = useState<Installment | null>(null);
    const [confirming, setConfirming] = useState(false);

    const fetchPlans = useCallback(async () => {
        try {
            const response = await installmentAPI.getCustomerPlans();
            setPlans(response.data);
        } catch (error: any) {
            console.error('Failed to fetch plans:', error);
            Alert.alert('Hata', 'Taksit planları yüklenemedi.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    const fetchInstallments = useCallback(async (planId: number) => {
        setDetailLoading(true);
        try {
            const response = await installmentAPI.getPlanInstallments(planId);
            setInstallments(response.data);
        } catch (error: any) {
            console.error('Failed to fetch installments:', error);
            Alert.alert('Hata', 'Taksitler yüklenemedi.');
        } finally {
            setDetailLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPlans();
    }, [fetchPlans]);

    const onRefresh = useCallback(() => {
        setRefreshing(true);
        fetchPlans();
    }, [fetchPlans]);

    const handlePlanPress = (plan: InstallmentPlan) => {
        setSelectedPlan(plan);
        fetchInstallments(plan.id);
    };

    const handleBackToList = () => {
        setSelectedPlan(null);
        setInstallments([]);
    };

    const handleConfirmPayment = (installment: Installment) => {
        setSelectedInstallment(installment);
        setConfirmModalVisible(true);
    };

    const confirmPayment = async () => {
        if (!selectedInstallment) return;

        setConfirming(true);
        try {
            await installmentAPI.customerConfirmPayment(selectedInstallment.id);
            Alert.alert('Başarılı', 'Ödeme bildiriminiz alınmıştır. Yönetici onayı bekleniyor.');
            setConfirmModalVisible(false);
            if (selectedPlan) {
                fetchInstallments(selectedPlan.id);
            }
        } catch (error: any) {
            console.error('Payment confirmation failed:', error);
            Alert.alert('Hata', 'Ödeme bildirimi gönderilemedi.');
        } finally {
            setConfirming(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'paid': return THEME.success;
            case 'customer_confirmed': return '#3B82F6';
            case 'overdue': return THEME.error;
            case 'pending': return THEME.warning;
            default: return THEME.textLight;
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('tr-TR', { day: '2-digit', month: 'long', year: 'numeric' });
    };

    const formatCurrency = (amount: string) => {
        return parseFloat(amount).toLocaleString('tr-TR', { minimumFractionDigits: 2 }) + ' ₺';
    };

    const renderPlanCard = ({ item }: { item: InstallmentPlan }) => (
        <TouchableOpacity style={styles.planCard} onPress={() => handlePlanPress(item)}>
            <View style={styles.planHeader}>
                <Text style={styles.productName} numberOfLines={1}>{item.product_name}</Text>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) + '20' }]}>
                    <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>
                        {item.status_display}
                    </Text>
                </View>
            </View>

            <View style={styles.progressSection}>
                <View style={styles.progressBar}>
                    <View style={[styles.progressFill, { width: `${item.progress_percentage}%` }]} />
                </View>
                <Text style={styles.progressText}>{item.progress_percentage}%</Text>
            </View>

            <View style={styles.planDetails}>
                <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Toplam:</Text>
                    <Text style={styles.detailValue}>{formatCurrency(item.total_amount)}</Text>
                </View>
                <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Ödenen:</Text>
                    <Text style={[styles.detailValue, { color: THEME.success }]}>{formatCurrency(item.paid_amount)}</Text>
                </View>
                <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Kalan:</Text>
                    <Text style={[styles.detailValue, { color: THEME.error }]}>{formatCurrency(item.remaining_amount)}</Text>
                </View>
            </View>

            <View style={styles.planFooter}>
                <FontAwesome name="calendar" size={14} color={THEME.textLight} />
                <Text style={styles.dateText}>{item.installment_count} Taksit • {formatDate(item.start_date)}</Text>
                <FontAwesome name="chevron-right" size={14} color={THEME.textLight} />
            </View>
        </TouchableOpacity>
    );

    const renderInstallmentItem = ({ item }: { item: Installment }) => (
        <View style={styles.installmentCard}>
            <View style={styles.installmentHeader}>
                <View style={styles.installmentNumber}>
                    <Text style={styles.installmentNumberText}>{item.installment_number}</Text>
                </View>
                <View style={styles.installmentInfo}>
                    <Text style={styles.installmentAmount}>{formatCurrency(item.amount)}</Text>
                    <Text style={styles.installmentDate}>Vade: {formatDate(item.due_date)}</Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) + '20' }]}>
                    <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>
                        {item.status_display}
                    </Text>
                </View>
            </View>

            {item.is_overdue && (
                <View style={styles.overdueWarning}>
                    <FontAwesome name="exclamation-triangle" size={14} color={THEME.error} />
                    <Text style={styles.overdueText}>{Math.abs(item.days_until_due)} gün gecikmiş</Text>
                </View>
            )}

            {(item.status === 'pending' || item.status === 'overdue') && (
                <TouchableOpacity
                    style={styles.confirmButton}
                    onPress={() => handleConfirmPayment(item)}
                >
                    <FontAwesome name="check" size={16} color="#FFF" />
                    <Text style={styles.confirmButtonText}>Ödedim</Text>
                </TouchableOpacity>
            )}

            {item.status === 'customer_confirmed' && (
                <View style={styles.waitingApproval}>
                    <FontAwesome name="clock-o" size={14} color="#3B82F6" />
                    <Text style={styles.waitingText}>Yönetici onayı bekleniyor</Text>
                </View>
            )}
        </View>
    );

    // Detail View
    if (selectedPlan) {
        return (
            <View style={styles.container}>
                <TouchableOpacity style={styles.backButton} onPress={handleBackToList}>
                    <FontAwesome name="arrow-left" size={18} color={THEME.primary} />
                    <Text style={styles.backText}>Geri</Text>
                </TouchableOpacity>

                <View style={styles.planSummary}>
                    <Text style={styles.summaryTitle}>{selectedPlan.product_name}</Text>
                    <View style={styles.summaryRow}>
                        <Text style={styles.summaryLabel}>Toplam: {formatCurrency(selectedPlan.total_amount)}</Text>
                        <Text style={styles.summaryLabel}>Kalan: {formatCurrency(selectedPlan.remaining_amount)}</Text>
                    </View>
                    <View style={styles.progressSection}>
                        <View style={styles.progressBar}>
                            <View style={[styles.progressFill, { width: `${selectedPlan.progress_percentage}%` }]} />
                        </View>
                        <Text style={styles.progressText}>{selectedPlan.progress_percentage}%</Text>
                    </View>
                </View>

                <Text style={styles.sectionTitle}>Taksitler</Text>

                {detailLoading ? (
                    <ActivityIndicator size="large" color={THEME.primary} style={{ marginTop: 40 }} />
                ) : (
                    <FlatList
                        data={installments}
                        renderItem={renderInstallmentItem}
                        keyExtractor={(item) => item.id.toString()}
                        contentContainerStyle={styles.listContent}
                        showsVerticalScrollIndicator={false}
                    />
                )}

                {/* Confirm Payment Modal */}
                <Modal visible={confirmModalVisible} transparent animationType="fade">
                    <View style={styles.modalOverlay}>
                        <View style={styles.modalContent}>
                            <Text style={styles.modalTitle}>Ödeme Bildirimi</Text>
                            {selectedInstallment && (
                                <>
                                    <Text style={styles.modalText}>
                                        {selectedInstallment.installment_number}. taksit ödemesinin ({formatCurrency(selectedInstallment.amount)}) yapıldığını onaylıyor musunuz?
                                    </Text>
                                    <Text style={styles.modalNote}>
                                        Yönetici onayladıktan sonra ödeme tamamlanacaktır.
                                    </Text>
                                </>
                            )}
                            <View style={styles.modalButtons}>
                                <TouchableOpacity
                                    style={styles.cancelButton}
                                    onPress={() => setConfirmModalVisible(false)}
                                    disabled={confirming}
                                >
                                    <Text style={styles.cancelButtonText}>İptal</Text>
                                </TouchableOpacity>
                                <TouchableOpacity
                                    style={styles.submitButton}
                                    onPress={confirmPayment}
                                    disabled={confirming}
                                >
                                    {confirming ? (
                                        <ActivityIndicator color="#FFF" size="small" />
                                    ) : (
                                        <Text style={styles.submitButtonText}>Ödedim</Text>
                                    )}
                                </TouchableOpacity>
                            </View>
                        </View>
                    </View>
                </Modal>
            </View>
        );
    }

    // List View
    return (
        <View style={styles.container}>
            {loading ? (
                <ActivityIndicator size="large" color={THEME.primary} style={{ marginTop: 40 }} />
            ) : plans.length === 0 ? (
                <View style={styles.emptyState}>
                    <FontAwesome name="credit-card" size={64} color={THEME.textLight} />
                    <Text style={styles.emptyTitle}>Taksit Planınız Yok</Text>
                    <Text style={styles.emptyText}>Henüz size atanmış bir taksit planı bulunmuyor.</Text>
                </View>
            ) : (
                <FlatList
                    data={plans}
                    renderItem={renderPlanCard}
                    keyExtractor={(item) => item.id.toString()}
                    contentContainerStyle={styles.listContent}
                    showsVerticalScrollIndicator={false}
                    refreshControl={
                        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={THEME.primary} />
                    }
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: THEME.background },
    listContent: { padding: 16 },

    // Plan Card
    planCard: {
        backgroundColor: THEME.card,
        borderRadius: 16,
        padding: 16,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
        elevation: 3,
    },
    planHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
    productName: { fontSize: 16, fontWeight: 'bold', color: THEME.text, flex: 1, marginRight: 8 },
    statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
    statusText: { fontSize: 12, fontWeight: '600' },

    // Progress
    progressSection: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
    progressBar: { flex: 1, height: 8, backgroundColor: THEME.border, borderRadius: 4, overflow: 'hidden' },
    progressFill: { height: '100%', backgroundColor: THEME.success, borderRadius: 4 },
    progressText: { marginLeft: 10, fontSize: 14, fontWeight: '600', color: THEME.text },

    // Details
    planDetails: { marginBottom: 12 },
    detailRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
    detailLabel: { fontSize: 14, color: THEME.textLight },
    detailValue: { fontSize: 14, fontWeight: '600', color: THEME.text },

    planFooter: { flexDirection: 'row', alignItems: 'center', paddingTop: 12, borderTopWidth: 1, borderTopColor: THEME.border },
    dateText: { flex: 1, marginLeft: 8, fontSize: 13, color: THEME.textLight },

    // Installment Card
    installmentCard: {
        backgroundColor: THEME.card,
        borderRadius: 12,
        padding: 14,
        marginBottom: 10,
        borderWidth: 1,
        borderColor: THEME.border,
    },
    installmentHeader: { flexDirection: 'row', alignItems: 'center' },
    installmentNumber: { width: 32, height: 32, borderRadius: 16, backgroundColor: THEME.primary, justifyContent: 'center', alignItems: 'center' },
    installmentNumberText: { color: '#FFF', fontWeight: 'bold', fontSize: 14 },
    installmentInfo: { flex: 1, marginLeft: 12 },
    installmentAmount: { fontSize: 16, fontWeight: 'bold', color: THEME.text },
    installmentDate: { fontSize: 13, color: THEME.textLight, marginTop: 2 },

    overdueWarning: { flexDirection: 'row', alignItems: 'center', marginTop: 10, padding: 8, backgroundColor: THEME.error + '15', borderRadius: 8 },
    overdueText: { marginLeft: 8, fontSize: 13, color: THEME.error, fontWeight: '500' },

    confirmButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 12, paddingVertical: 10, backgroundColor: THEME.success, borderRadius: 10 },
    confirmButtonText: { color: '#FFF', fontWeight: '600', marginLeft: 8 },

    waitingApproval: { flexDirection: 'row', alignItems: 'center', marginTop: 10, paddingVertical: 8, paddingHorizontal: 12, backgroundColor: '#3B82F615', borderRadius: 8 },
    waitingText: { marginLeft: 8, fontSize: 13, color: '#3B82F6' },

    // Back Button
    backButton: { flexDirection: 'row', alignItems: 'center', padding: 16, paddingBottom: 8 },
    backText: { marginLeft: 8, fontSize: 16, color: THEME.primary, fontWeight: '500' },

    // Plan Summary
    planSummary: { backgroundColor: THEME.card, padding: 16, marginHorizontal: 16, borderRadius: 12, marginBottom: 16 },
    summaryTitle: { fontSize: 18, fontWeight: 'bold', color: THEME.text, marginBottom: 8 },
    summaryRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
    summaryLabel: { fontSize: 14, color: THEME.textLight },

    sectionTitle: { fontSize: 16, fontWeight: '600', color: THEME.text, marginHorizontal: 16, marginBottom: 8 },

    // Empty State
    emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
    emptyTitle: { fontSize: 20, fontWeight: 'bold', color: THEME.text, marginTop: 20 },
    emptyText: { fontSize: 14, color: THEME.textLight, textAlign: 'center', marginTop: 8 },

    // Modal
    modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
    modalContent: { backgroundColor: '#FFF', borderRadius: 20, padding: 24, marginHorizontal: 24, width: '85%' },
    modalTitle: { fontSize: 20, fontWeight: 'bold', color: THEME.text, textAlign: 'center', marginBottom: 16 },
    modalText: { fontSize: 15, color: THEME.text, textAlign: 'center', marginBottom: 12, lineHeight: 22 },
    modalNote: { fontSize: 13, color: THEME.textLight, textAlign: 'center', marginBottom: 20 },
    modalButtons: { flexDirection: 'row', justifyContent: 'space-between' },
    cancelButton: { flex: 1, paddingVertical: 12, marginRight: 8, borderRadius: 10, borderWidth: 1, borderColor: THEME.border, alignItems: 'center' },
    cancelButtonText: { fontSize: 15, color: THEME.text, fontWeight: '600' },
    submitButton: { flex: 1, paddingVertical: 12, marginLeft: 8, borderRadius: 10, backgroundColor: THEME.success, alignItems: 'center' },
    submitButtonText: { fontSize: 15, color: '#FFF', fontWeight: '600' },
});
