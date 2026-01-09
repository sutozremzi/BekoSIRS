// components/ProductComparisonModal.tsx
/**
 * Product Comparison Modal Component
 * 
 * Displays a side-by-side comparison of selected products.
 * Features:
 * - Up to 4 products comparison
 * - Highlight differences in green/red
 * - Best value recommendation
 * 
 * Usage:
 * <ProductComparisonModal
 *   visible={showComparison}
 *   onClose={() => setShowComparison(false)}
 *   productIds={[1, 2, 3]}
 * />
 */

import React, { useEffect, useState } from 'react';
import {
    Modal,
    View,
    Text,
    StyleSheet,
    ScrollView,
    TouchableOpacity,
    ActivityIndicator,
    Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// Types
interface Product {
    id: number;
    name: string;
    brand: string;
    price: string;
    category_name?: string;
    image?: string;
    warranty_duration_months: number;
    stock: number;
}

interface ComparisonField {
    key: string;
    label: string;
    unit?: string;
    type: 'currency' | 'text' | 'number';
}

interface Difference {
    is_different: boolean;
    values: any[];
    best_indices: number[];
}

interface ComparisonData {
    products: Product[];
    comparison_fields: ComparisonField[];
    differences: Record<string, Difference>;
    recommendation: {
        indices: number[];
        product_ids: number[];
        reason: string;
    };
}

interface Props {
    visible: boolean;
    onClose: () => void;
    productIds: number[];
    apiToken?: string;
}

const API_BASE = 'http://127.0.0.1:8000/api/v1';

export default function ProductComparisonModal({ visible, onClose, productIds, apiToken }: Props) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<ComparisonData | null>(null);

    useEffect(() => {
        if (visible && productIds.length >= 2) {
            fetchComparison();
        }
    }, [visible, productIds]);

    const fetchComparison = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_BASE}/products/compare/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(apiToken ? { Authorization: `Bearer ${apiToken}` } : {}),
                },
                body: JSON.stringify({ product_ids: productIds }),
            });

            if (!response.ok) {
                throw new Error('Karşılaştırma yüklenemedi');
            }

            const result = await response.json();
            setData(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Bir hata oluştu');
        } finally {
            setLoading(false);
        }
    };

    const renderValue = (field: ComparisonField, value: any, isBest: boolean) => {
        let displayValue = value;

        if (field.type === 'currency') {
            displayValue = `${value}₺`;
        } else if (field.unit) {
            displayValue = `${value} ${field.unit}`;
        }

        return (
            <View style={[styles.valueCell, isBest && styles.bestValue]}>
                <Text style={[styles.valueText, isBest && styles.bestValueText]}>
                    {displayValue || '-'}
                </Text>
                {isBest && (
                    <Ionicons name="checkmark-circle" size={14} color="#16a34a" style={styles.bestIcon} />
                )}
            </View>
        );
    };

    if (!visible) return null;

    return (
        <Modal
            visible={visible}
            animationType="slide"
            transparent={true}
            onRequestClose={onClose}
        >
            <View style={styles.overlay}>
                <View style={styles.container}>
                    {/* Header */}
                    <View style={styles.header}>
                        <Text style={styles.headerTitle}>Ürün Karşılaştırma</Text>
                        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                            <Ionicons name="close" size={24} color="#6b7280" />
                        </TouchableOpacity>
                    </View>

                    {/* Content */}
                    {loading ? (
                        <View style={styles.loadingContainer}>
                            <ActivityIndicator size="large" color="#2563eb" />
                            <Text style={styles.loadingText}>Karşılaştırılıyor...</Text>
                        </View>
                    ) : error ? (
                        <View style={styles.errorContainer}>
                            <Ionicons name="alert-circle" size={48} color="#dc2626" />
                            <Text style={styles.errorText}>{error}</Text>
                            <TouchableOpacity onPress={fetchComparison} style={styles.retryButton}>
                                <Text style={styles.retryText}>Tekrar Dene</Text>
                            </TouchableOpacity>
                        </View>
                    ) : data ? (
                        <ScrollView style={styles.scrollView}>
                            {/* Product Headers */}
                            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                                <View>
                                    {/* Product Images & Names */}
                                    <View style={styles.row}>
                                        <View style={styles.labelCell}>
                                            <Text style={styles.labelText}>Ürün</Text>
                                        </View>
                                        {data.products.map((product, idx) => (
                                            <View key={product.id} style={styles.productHeader}>
                                                <View style={[
                                                    styles.productImageContainer,
                                                    data.recommendation.indices.includes(idx) && styles.recommendedBorder
                                                ]}>
                                                    {product.image ? (
                                                        <Image source={{ uri: product.image }} style={styles.productImage} />
                                                    ) : (
                                                        <Ionicons name="cube-outline" size={40} color="#9ca3af" />
                                                    )}
                                                    {data.recommendation.indices.includes(idx) && (
                                                        <View style={styles.recommendedBadge}>
                                                            <Text style={styles.recommendedText}>⭐ Önerilen</Text>
                                                        </View>
                                                    )}
                                                </View>
                                                <Text style={styles.productName} numberOfLines={2}>
                                                    {product.name}
                                                </Text>
                                                <Text style={styles.productBrand}>{product.brand}</Text>
                                            </View>
                                        ))}
                                    </View>

                                    {/* Comparison Fields */}
                                    {data.comparison_fields.map((field) => {
                                        const diff = data.differences[field.key];
                                        return (
                                            <View key={field.key} style={[styles.row, diff?.is_different && styles.highlightRow]}>
                                                <View style={styles.labelCell}>
                                                    <Text style={styles.labelText}>{field.label}</Text>
                                                </View>
                                                {diff?.values.map((value, idx) => (
                                                    <View key={idx}>
                                                        {renderValue(field, value, diff.best_indices.includes(idx))}
                                                    </View>
                                                ))}
                                            </View>
                                        );
                                    })}
                                </View>
                            </ScrollView>

                            {/* Recommendation */}
                            {data.recommendation.indices.length > 0 && (
                                <View style={styles.recommendationBox}>
                                    <Ionicons name="star" size={20} color="#f59e0b" />
                                    <Text style={styles.recommendationText}>
                                        <Text style={styles.recommendationBold}>Öneri: </Text>
                                        {data.products[data.recommendation.indices[0]]?.name} - {data.recommendation.reason}
                                    </Text>
                                </View>
                            )}
                        </ScrollView>
                    ) : null}
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        justifyContent: 'flex-end',
    },
    container: {
        backgroundColor: '#fff',
        borderTopLeftRadius: 20,
        borderTopRightRadius: 20,
        maxHeight: '90%',
        minHeight: '60%',
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#e5e7eb',
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#111827',
    },
    closeButton: {
        padding: 4,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 40,
    },
    loadingText: {
        marginTop: 12,
        fontSize: 16,
        color: '#6b7280',
    },
    errorContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 40,
    },
    errorText: {
        marginTop: 12,
        fontSize: 16,
        color: '#dc2626',
        textAlign: 'center',
    },
    retryButton: {
        marginTop: 16,
        paddingHorizontal: 24,
        paddingVertical: 12,
        backgroundColor: '#2563eb',
        borderRadius: 8,
    },
    retryText: {
        color: '#fff',
        fontWeight: '600',
    },
    scrollView: {
        flex: 1,
        padding: 16,
    },
    row: {
        flexDirection: 'row',
        borderBottomWidth: 1,
        borderBottomColor: '#f3f4f6',
    },
    highlightRow: {
        backgroundColor: '#fef3c7',
    },
    labelCell: {
        width: 100,
        padding: 12,
        justifyContent: 'center',
        backgroundColor: '#f9fafb',
    },
    labelText: {
        fontSize: 12,
        fontWeight: '600',
        color: '#6b7280',
    },
    valueCell: {
        width: 120,
        padding: 12,
        justifyContent: 'center',
        alignItems: 'center',
        flexDirection: 'row',
    },
    valueText: {
        fontSize: 14,
        color: '#111827',
        textAlign: 'center',
    },
    bestValue: {
        backgroundColor: '#dcfce7',
    },
    bestValueText: {
        color: '#16a34a',
        fontWeight: '600',
    },
    bestIcon: {
        marginLeft: 4,
    },
    productHeader: {
        width: 120,
        padding: 12,
        alignItems: 'center',
    },
    productImageContainer: {
        width: 80,
        height: 80,
        borderRadius: 8,
        backgroundColor: '#f3f4f6',
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 8,
        overflow: 'hidden',
        borderWidth: 2,
        borderColor: 'transparent',
    },
    recommendedBorder: {
        borderColor: '#f59e0b',
    },
    productImage: {
        width: '100%',
        height: '100%',
        resizeMode: 'cover',
    },
    recommendedBadge: {
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#f59e0b',
        paddingVertical: 2,
    },
    recommendedText: {
        fontSize: 10,
        color: '#fff',
        textAlign: 'center',
        fontWeight: '600',
    },
    productName: {
        fontSize: 12,
        fontWeight: '500',
        color: '#111827',
        textAlign: 'center',
    },
    productBrand: {
        fontSize: 11,
        color: '#6b7280',
        textAlign: 'center',
    },
    recommendationBox: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#fffbeb',
        padding: 16,
        borderRadius: 12,
        marginTop: 16,
        marginBottom: 24,
    },
    recommendationText: {
        flex: 1,
        marginLeft: 12,
        fontSize: 14,
        color: '#92400e',
    },
    recommendationBold: {
        fontWeight: '600',
    },
});
