import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  SafeAreaView,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Text,
  View,
  TouchableOpacity,
  RefreshControl,
  Modal,
  TextInput,
  Alert,
  ScrollView,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { FontAwesome } from '@expo/vector-icons';
import { serviceRequestAPI, productOwnershipAPI, assignmentAPI } from '../../services';
import { useLanguage } from '../../context/LanguageContext';
import { t } from '../../i18n';

interface ServiceRequest {
  id: number;
  customer_name: string;
  product_name: string;
  request_type: string;
  status: string;
  description: string;
  created_at: string;
  queue_entry?: {
    queue_number: number;
    priority: number;
    estimated_wait_time: number;
  };
}

// Hem ProductOwnership hem ProductAssignment için ortak tip
interface ProductOption {
  id: number;
  type: 'ownership' | 'assignment';
  product: {
    id: number;
    name: string;
    brand: string;
  };
}

const ServiceRequestsScreen = () => {
  const params = useLocalSearchParams();
  const { language } = useLanguage();
  const [requests, setRequests] = useState<ServiceRequest[]>([]);

  const StatusConfig: Record<string, { label: string; color: string; icon: string }> = {
    pending: { label: t('service.pending'), color: '#FF9800', icon: 'clock-o' },
    in_queue: { label: t('service.inQueue'), color: '#2196F3', icon: 'list-ol' },
    in_progress: { label: t('service.inProgress'), color: '#9C27B0', icon: 'cog' },
    completed: { label: t('service.completed'), color: '#4CAF50', icon: 'check-circle' },
    cancelled: { label: t('service.cancelled'), color: '#f44336', icon: 'times-circle' },
  };

  const RequestTypeConfig: Record<string, string> = {
    repair: t('service.repair'),
    maintenance: t('service.maintenance'),
    warranty: t('service.warranty'),
    complaint: t('service.complaint'),
    other: t('service.other'),
  };
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Params-based modal already handled flag
  const paramsHandledRef = useRef(false);

  // Form state
  const [selectedProduct, setSelectedProduct] = useState<number | null>(null);
  const [requestType, setRequestType] = useState<string>('repair');
  const [description, setDescription] = useState('');
  const [productPickerOpen, setProductPickerOpen] = useState(false);
  const [typePickerOpen, setTypePickerOpen] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [requestsRes, ownershipsRes, assignmentsRes] = await Promise.all([
        serviceRequestAPI.getMyRequests().catch(() => ({ data: [] })),
        productOwnershipAPI.getMyOwnerships().catch(() => ({ data: [] })),
        assignmentAPI.getMyAssignments().catch(() => ({ data: [] })),
      ]);

      const requestsData = requestsRes.data?.results ?? requestsRes.data ?? [];
      setRequests(Array.isArray(requestsData) ? requestsData : []);

      // Owned products (delivered)
      const ownerships: ProductOption[] = (Array.isArray(ownershipsRes.data) ? ownershipsRes.data : [])
        .map((o: any) => ({ id: o.id, type: 'ownership' as const, product: o.product }));

      // Assigned products (pending delivery) — exclude duplicates already in ownerships
      const ownedProductIds = new Set(ownerships.map(o => o.product.id));
      const assignmentsData = assignmentsRes.data?.results || assignmentsRes.data || [];
      const assignments: ProductOption[] = (Array.isArray(assignmentsData) ? assignmentsData : [])
        .filter((a: any) => !ownedProductIds.has(a.product?.id))
        .map((a: any) => ({ id: a.id, type: 'assignment' as const, product: a.product }));

      setProducts([...ownerships, ...assignments]);
    } catch (error) {
      console.error('Service requests fetch error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, [fetchData]);

  // Reset ref when params change (new navigation)
  useEffect(() => {
    paramsHandledRef.current = false;
  }, [params.openModal, params.productId]);

  // Handle params for auto-open — only fire once per navigation
  useEffect(() => {
    if (params.openModal === 'true' && products.length > 0 && !paramsHandledRef.current) {
      paramsHandledRef.current = true;
      setModalVisible(true);
      if (params.productId) {
        const pId = Number(params.productId);
        const option = products.find(p => p.product.id === pId);
        if (option) {
          setSelectedProduct(option.id);
        }
      }
    }
  }, [params, products]);

  const handleCreateRequest = async () => {
    if (!selectedProduct) {
      Alert.alert(t('common.error'), t('service.selectProductError'));
      return;
    }
    if (!description.trim()) {
      Alert.alert(t('common.error'), t('service.descriptionError'));
      return;
    }

    setSubmitting(true);
    try {
      const selectedOption = products.find(p => p.id === selectedProduct);
      await serviceRequestAPI.createRequest(
        selectedProduct,
        requestType as any,
        description,
        selectedOption?.type === 'assignment' ? 'assignment' : 'ownership'
      );
      Alert.alert(t('common.success'), t('service.created'));
      setModalVisible(false);
      setSelectedProduct(null);
      setRequestType('repair');
      setDescription('');
      fetchData();
    } catch (error) {
      Alert.alert(t('common.error'), t('service.createFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateString: string) => {
    const locale = language === 'tr' ? 'tr-TR' : 'en-US';
    return new Date(dateString).toLocaleDateString(locale, {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  const renderItem = ({ item }: { item: ServiceRequest }) => {
    const statusConfig = StatusConfig[item.status] || StatusConfig.pending;

    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={styles.idContainer}>
            <Text style={styles.requestId}>SR-{item.id}</Text>
            <Text style={styles.requestType}>
              {RequestTypeConfig[item.request_type] || item.request_type}
            </Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: statusConfig.color }]}>
            <FontAwesome name={statusConfig.icon as any} size={12} color="#fff" />
            <Text style={styles.statusText}>{statusConfig.label}</Text>
          </View>
        </View>

        <Text style={styles.productName}>{item.product_name}</Text>
        <Text style={styles.description} numberOfLines={2}>
          {item.description}
        </Text>

        {item.queue_entry && item.status === 'in_queue' && (
          <View style={styles.queueInfo}>
            <FontAwesome name="list-ol" size={14} color="#2196F3" />
            <Text style={styles.queueText}>
              Sıra No: {item.queue_entry.queue_number} | {t('service.estimatedWait')}: {item.queue_entry.estimated_wait_time} {t('service.minutes')}
            </Text>
          </View>
        )}

        <View style={styles.footer}>
          <Text style={styles.date}>{formatDate(item.created_at)}</Text>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#000000" testID="loading-sr" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={requests}
        renderItem={renderItem}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.headerTitle}>{t('service.title')}</Text>
            <TouchableOpacity
              style={styles.addButton}
              onPress={() => setModalVisible(true)}
            >
              <FontAwesome name="plus" size={16} color="#fff" />
              <Text style={styles.addButtonText}>{t('service.newRequest')}</Text>
            </TouchableOpacity>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <FontAwesome name="wrench" size={80} color="#ccc" />
            <Text style={styles.emptyTitle}>{t('service.noRequests')}</Text>
            <Text style={styles.emptyText}>
              {t('service.noRequestsDesc')}
            </Text>
          </View>
        }
      />

      {/* Create Request Modal */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{t('service.newServiceRequest')}</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <FontAwesome name="times" size={24} color="#333" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <Text style={styles.label}>{t('service.selectProduct')} ({products.length})</Text>
              <TouchableOpacity
                style={styles.selectorButton}
                onPress={() => setProductPickerOpen(!productPickerOpen)}
              >
                <Text style={selectedProduct ? styles.selectorText : styles.selectorPlaceholder}>
                  {selectedProduct
                    ? (() => { const p = products.find(x => x.id === selectedProduct); return p ? p.product.name : t('service.selectProductPlaceholder'); })()
                    : t('service.selectProductPlaceholder')}
                </Text>
                <FontAwesome name={productPickerOpen ? 'chevron-up' : 'chevron-down'} size={14} color="#666" />
              </TouchableOpacity>
              {productPickerOpen && (
                <View style={styles.selectorList}>
                  {products.length === 0 ? (
                    <Text style={styles.selectorEmpty}>{t('service.noProducts')}</Text>
                  ) : (
                    products.map((p: ProductOption) => (
                      <TouchableOpacity
                        key={`${p.type}-${p.id}`}
                        style={[styles.selectorItem, selectedProduct === p.id && styles.selectorItemActive]}
                        onPress={() => { setSelectedProduct(p.id); setProductPickerOpen(false); }}
                      >
                        <Text style={[styles.selectorItemText, selectedProduct === p.id && styles.selectorItemTextActive]}>
                          {p.product.name}{p.product.brand ? ` - ${p.product.brand}` : ''}{p.type === 'assignment' ? ` (${t('service.pendingDelivery')})` : ''}
                        </Text>
                      </TouchableOpacity>
                    ))
                  )}
                </View>
              )}

              <Text style={styles.label}>{t('service.requestType')}</Text>
              <TouchableOpacity
                style={styles.selectorButton}
                onPress={() => setTypePickerOpen(!typePickerOpen)}
              >
                <Text style={styles.selectorText}>
                  {RequestTypeConfig[requestType] || t('service.repair')}
                </Text>
                <FontAwesome name={typePickerOpen ? 'chevron-up' : 'chevron-down'} size={14} color="#666" />
              </TouchableOpacity>
              {typePickerOpen && (
                <View style={styles.selectorList}>
                  {Object.entries(RequestTypeConfig).map(([val, label]) => (
                    <TouchableOpacity
                      key={val}
                      style={[styles.selectorItem, requestType === val && styles.selectorItemActive]}
                      onPress={() => { setRequestType(val); setTypePickerOpen(false); }}
                    >
                      <Text style={[styles.selectorItemText, requestType === val && styles.selectorItemTextActive]}>{label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}

              <Text style={styles.label}>{t('service.description')}</Text>
              <TextInput
                style={styles.textArea}
                multiline
                numberOfLines={4}
                placeholder={t('service.descriptionPlaceholder')}
                value={description}
                onChangeText={setDescription}
                textAlignVertical="top"
              />
            </ScrollView>

            <View style={styles.modalFooter}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setModalVisible(false)}
              >
                <Text style={styles.cancelButtonText}>{t('common.cancel')}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.submitButton, submitting && styles.disabledButton]}
                onPress={handleCreateRequest}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.submitButtonText}>{t('service.submit')}</Text>
                )}
              </TouchableOpacity>
            </View>
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
  list: {
    paddingHorizontal: 15,
    paddingBottom: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 10,
    marginBottom: 20,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#000000',
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#000000',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginBottom: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  idContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  requestId: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#000000',
  },
  requestType: {
    fontSize: 12,
    color: '#666',
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  productName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 6,
  },
  description: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  queueInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
    padding: 10,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  queueText: {
    fontSize: 13,
    color: '#2196F3',
    fontWeight: '500',
  },
  footer: {
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  date: {
    fontSize: 12,
    color: '#999',
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 20,
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
    textAlign: 'center',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  modalBody: {
    padding: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
    marginTop: 12,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    backgroundColor: '#f9f9f9',
  },
  selectorButton: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    backgroundColor: '#f9f9f9',
    paddingHorizontal: 14,
    paddingVertical: 14,
  },
  selectorText: {
    fontSize: 14,
    color: '#333',
    flex: 1,
  },
  selectorPlaceholder: {
    fontSize: 14,
    color: '#999',
    flex: 1,
  },
  selectorList: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    backgroundColor: '#fff',
    marginTop: 4,
    overflow: 'hidden',
  },
  selectorItem: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  selectorItemActive: {
    backgroundColor: '#000',
  },
  selectorItemText: {
    fontSize: 14,
    color: '#333',
  },
  selectorItemTextActive: {
    color: '#fff',
    fontWeight: '600',
  },
  selectorEmpty: {
    padding: 14,
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
  },
  textArea: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    minHeight: 100,
    backgroundColor: '#f9f9f9',
  },
  modalFooter: {
    flexDirection: 'row',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    color: '#666',
    fontWeight: '600',
  },
  submitButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 8,
    backgroundColor: '#000000',
    alignItems: 'center',
  },
  submitButtonText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
  },
  disabledButton: {
    opacity: 0.6,
  },
});

export default ServiceRequestsScreen;
