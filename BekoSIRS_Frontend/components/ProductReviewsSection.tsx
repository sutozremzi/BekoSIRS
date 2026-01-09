// components/ProductReviewsSection.tsx
/**
 * Product Reviews Section Component
 * 
 * Displays product reviews and allows adding new reviews.
 * Features:
 * - Star rating display
 * - Review list with pagination
 * - Add review modal
 * 
 * Usage:
 * <ProductReviewsSection productId={123} />
 */

import React, { useEffect, useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    FlatList,
    TouchableOpacity,
    TextInput,
    Modal,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// Types
interface Review {
    id: number;
    customer_name: string;
    rating: number;
    comment: string;
    created_at: string;
}

interface Props {
    productId: number;
    apiToken?: string;
    canAddReview?: boolean;
}

const API_BASE = 'http://127.0.0.1:8000/api/v1';

export default function ProductReviewsSection({ productId, apiToken, canAddReview = true }: Props) {
    const [reviews, setReviews] = useState<Review[]>([]);
    const [loading, setLoading] = useState(false);
    const [showAddModal, setShowAddModal] = useState(false);
    const [rating, setRating] = useState(5);
    const [comment, setComment] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [averageRating, setAverageRating] = useState(0);

    useEffect(() => {
        fetchReviews();
    }, [productId]);

    const fetchReviews = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE}/reviews/product/${productId}/`, {
                headers: apiToken ? { Authorization: `Bearer ${apiToken}` } : {},
            });

            if (response.ok) {
                const data = await response.json();
                setReviews(data.reviews || data);

                // Calculate average
                if (data.length > 0) {
                    const avg = data.reduce((sum: number, r: Review) => sum + r.rating, 0) / data.length;
                    setAverageRating(Math.round(avg * 10) / 10);
                }
            }
        } catch (err) {
            console.error('Failed to fetch reviews:', err);
        } finally {
            setLoading(false);
        }
    };

    const submitReview = async () => {
        if (!comment.trim()) {
            Alert.alert('Hata', 'Lütfen bir yorum yazın.');
            return;
        }

        setSubmitting(true);
        try {
            const response = await fetch(`${API_BASE}/reviews/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(apiToken ? { Authorization: `Bearer ${apiToken}` } : {}),
                },
                body: JSON.stringify({
                    product: productId,
                    rating,
                    comment: comment.trim(),
                }),
            });

            if (response.ok) {
                Alert.alert('Başarılı', 'Yorumunuz gönderildi. Onaylandıktan sonra görünecektir.');
                setShowAddModal(false);
                setComment('');
                setRating(5);
                fetchReviews();
            } else {
                const error = await response.json();
                Alert.alert('Hata', error.detail || 'Yorum gönderilemedi.');
            }
        } catch (err) {
            Alert.alert('Hata', 'Bir hata oluştu. Lütfen tekrar deneyin.');
        } finally {
            setSubmitting(false);
        }
    };

    const renderStars = (count: number, size: number = 16, interactive: boolean = false, onPress?: (n: number) => void) => {
        return (
            <View style={styles.starsContainer}>
                {[1, 2, 3, 4, 5].map((n) => (
                    <TouchableOpacity
                        key={n}
                        onPress={() => interactive && onPress?.(n)}
                        disabled={!interactive}
                    >
                        <Ionicons
                            name={n <= count ? 'star' : 'star-outline'}
                            size={size}
                            color={n <= count ? '#f59e0b' : '#d1d5db'}
                            style={styles.star}
                        />
                    </TouchableOpacity>
                ))}
            </View>
        );
    };

    const renderReviewItem = ({ item }: { item: Review }) => (
        <View style={styles.reviewCard}>
            <View style={styles.reviewHeader}>
                <View style={styles.avatar}>
                    <Text style={styles.avatarText}>
                        {item.customer_name?.charAt(0).toUpperCase() || 'K'}
                    </Text>
                </View>
                <View style={styles.reviewMeta}>
                    <Text style={styles.customerName}>{item.customer_name || 'Müşteri'}</Text>
                    <Text style={styles.reviewDate}>
                        {new Date(item.created_at).toLocaleDateString('tr-TR')}
                    </Text>
                </View>
                {renderStars(item.rating)}
            </View>
            <Text style={styles.reviewComment}>{item.comment}</Text>
        </View>
    );

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <View>
                    <Text style={styles.title}>Müşteri Yorumları</Text>
                    <View style={styles.ratingRow}>
                        {renderStars(Math.round(averageRating), 20)}
                        <Text style={styles.avgRating}>{averageRating.toFixed(1)}</Text>
                        <Text style={styles.reviewCount}>({reviews.length} yorum)</Text>
                    </View>
                </View>
                {canAddReview && (
                    <TouchableOpacity
                        style={styles.addButton}
                        onPress={() => setShowAddModal(true)}
                    >
                        <Ionicons name="add" size={20} color="#fff" />
                        <Text style={styles.addButtonText}>Yorum Yap</Text>
                    </TouchableOpacity>
                )}
            </View>

            {/* Reviews List */}
            {loading ? (
                <ActivityIndicator size="large" color="#2563eb" style={styles.loader} />
            ) : reviews.length === 0 ? (
                <View style={styles.emptyState}>
                    <Ionicons name="chatbubbles-outline" size={48} color="#d1d5db" />
                    <Text style={styles.emptyText}>Henüz yorum yok</Text>
                    <Text style={styles.emptySubtext}>İlk yorumu siz yapın!</Text>
                </View>
            ) : (
                <FlatList
                    data={reviews}
                    renderItem={renderReviewItem}
                    keyExtractor={(item) => item.id.toString()}
                    scrollEnabled={false}
                    showsVerticalScrollIndicator={false}
                />
            )}

            {/* Add Review Modal */}
            <Modal
                visible={showAddModal}
                animationType="slide"
                transparent={true}
                onRequestClose={() => setShowAddModal(false)}
            >
                <View style={styles.modalOverlay}>
                    <View style={styles.modalContent}>
                        <View style={styles.modalHeader}>
                            <Text style={styles.modalTitle}>Yorum Ekle</Text>
                            <TouchableOpacity onPress={() => setShowAddModal(false)}>
                                <Ionicons name="close" size={24} color="#6b7280" />
                            </TouchableOpacity>
                        </View>

                        <Text style={styles.label}>Puanınız</Text>
                        <View style={styles.ratingSelector}>
                            {renderStars(rating, 32, true, setRating)}
                        </View>

                        <Text style={styles.label}>Yorumunuz</Text>
                        <TextInput
                            style={styles.textArea}
                            placeholder="Ürün hakkındaki düşüncelerinizi paylaşın..."
                            multiline
                            numberOfLines={4}
                            value={comment}
                            onChangeText={setComment}
                            textAlignVertical="top"
                        />

                        <TouchableOpacity
                            style={[styles.submitButton, submitting && styles.submitDisabled]}
                            onPress={submitReview}
                            disabled={submitting}
                        >
                            {submitting ? (
                                <ActivityIndicator color="#fff" />
                            ) : (
                                <>
                                    <Ionicons name="send" size={18} color="#fff" />
                                    <Text style={styles.submitText}>Gönder</Text>
                                </>
                            )}
                        </TouchableOpacity>
                    </View>
                </View>
            </Modal>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        marginTop: 24,
        paddingHorizontal: 16,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 16,
    },
    title: {
        fontSize: 18,
        fontWeight: '600',
        color: '#111827',
    },
    ratingRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 4,
    },
    avgRating: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
        marginLeft: 8,
    },
    reviewCount: {
        fontSize: 14,
        color: '#6b7280',
        marginLeft: 4,
    },
    addButton: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#2563eb',
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 8,
    },
    addButtonText: {
        color: '#fff',
        fontWeight: '600',
        marginLeft: 4,
    },
    loader: {
        marginVertical: 40,
    },
    emptyState: {
        alignItems: 'center',
        paddingVertical: 40,
    },
    emptyText: {
        fontSize: 16,
        color: '#6b7280',
        marginTop: 12,
    },
    emptySubtext: {
        fontSize: 14,
        color: '#9ca3af',
        marginTop: 4,
    },
    reviewCard: {
        backgroundColor: '#f9fafb',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
    },
    reviewHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    avatar: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: '#2563eb',
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 12,
    },
    avatarText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
    reviewMeta: {
        flex: 1,
    },
    customerName: {
        fontSize: 14,
        fontWeight: '600',
        color: '#111827',
    },
    reviewDate: {
        fontSize: 12,
        color: '#6b7280',
    },
    starsContainer: {
        flexDirection: 'row',
    },
    star: {
        marginHorizontal: 1,
    },
    reviewComment: {
        fontSize: 14,
        color: '#374151',
        lineHeight: 20,
    },
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
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
        marginBottom: 20,
    },
    modalTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#111827',
    },
    label: {
        fontSize: 14,
        fontWeight: '500',
        color: '#374151',
        marginBottom: 8,
        marginTop: 12,
    },
    ratingSelector: {
        alignItems: 'center',
        paddingVertical: 8,
    },
    textArea: {
        borderWidth: 1,
        borderColor: '#d1d5db',
        borderRadius: 8,
        padding: 12,
        fontSize: 14,
        minHeight: 100,
    },
    submitButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#2563eb',
        paddingVertical: 14,
        borderRadius: 8,
        marginTop: 20,
        marginBottom: 20,
    },
    submitDisabled: {
        backgroundColor: '#9ca3af',
    },
    submitText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
        marginLeft: 8,
    },
});
