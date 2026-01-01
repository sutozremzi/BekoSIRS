import React, { useEffect, useState, useCallback } from 'react';
import {
  SafeAreaView,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Text,
  View,
  TouchableOpacity,
  RefreshControl,
  Image,
  Alert,
} from 'react-native';
import { FontAwesome } from '@expo/vector-icons';
import { recommendationAPI, wishlistAPI, viewHistoryAPI } from '../../services/api';

interface Recommendation {
  id: number;
  product: {
    id: number;
    name: string;
    brand: string;
    price: string;
    stock: number;
    image?: string;
    category_name?: string; // Ensure this matches your serializer
  };
  score: number; // This is the ML score (0.0 to 1.0)
  reason: string;
  is_shown: boolean;
  clicked: boolean;
}

const RecommendationsScreen = () => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [generating, setGenerating] = useState(false);

  const fetchRecommendations = useCallback(async () => {
    try {
      const response = await recommendationAPI.getRecommendations();
      setRecommendations(response.data);
    } catch (error) {
      console.error('Recommendations fetch error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchRecommendations();
  }, [fetchRecommendations]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchRecommendations();
  }, [fetchRecommendations]);

  const handleGenerateRecommendations = async () => {
    setGenerating(true);
    try {
      const response = await recommendationAPI.generateRecommendations();
      Alert.alert(
        'Başarılı',
        `${response.data.recommendations_count} yeni öneri oluşturuldu!`
      );
      fetchRecommendations();
    } catch (error) {
      Alert.alert('Hata', 'Öneriler oluşturulamadı');
    } finally {
      setGenerating(false);
    }
  };

  const handleProductClick = async (recommendation: Recommendation) => {
    try {
      await Promise.all([
        recommendationAPI.recordClick(recommendation.id),
        viewHistoryAPI.recordView(recommendation.product.id),
      ]);
      setRecommendations((prev) =>
        prev.map((r) =>
          r.id === recommendation.id ? { ...r, clicked: true } : r
        )
      );
    } catch (error) {
      console.log('Click recording failed:', error);
    }
  };

  const handleAddToWishlist = async (productId: number, productName: string) => {
    try {
      await wishlistAPI.addItem(productId);
      Alert.alert('Başarılı', `"${productName}" istek listenize eklendi!`);
    } catch (error: any) {
      if (error.response?.data?.error) {
        Alert.alert('Bilgi', error.response.data.error);
      } else {
        Alert.alert('Hata', 'Ürün eklenemedi');
      }
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return '#4CAF50'; // Green for high match
    if (score >= 0.5) return '#FF9800'; // Orange for medium
    return '#2196F3'; // Blue for base
  };

  const renderItem = ({ item }: { item: Recommendation }) => {
    const product = item.product;
    const isInStock = product.stock > 0;

    // Convert ML score (0-1) to Percentage (0-100)
    const matchPercentage = Math.round(item.score * 100);

    return (
      <TouchableOpacity
        style={[styles.card, item.clicked && styles.clickedCard]}
        onPress={() => handleProductClick(item)}
        activeOpacity={0.7}
      >
        {/* Match Score Badge (ML Percentage) */}
        <View style={[styles.scoreBadge, { backgroundColor: getScoreColor(item.score) }]}>
          <Text style={styles.scoreText}>%{matchPercentage} Eşleşme</Text>
        </View>

        <View style={styles.cardContent}>
          {product.image ? (
            <Image source={{ uri: product.image }} style={styles.image} />
          ) : (
            <View style={[styles.image, styles.imagePlaceholder]}>
              <FontAwesome name="image" size={40} color="#ccc" />
            </View>
          )}

          <View style={styles.info}>
            <Text style={styles.productName} numberOfLines={2}>
              {product.name}
            </Text>
            
            {/* 🆕 ADDED: Category Name */}
            {product.category_name && (
              <Text style={styles.categoryText}>
                {product.category_name}
              </Text>
            )}

            <Text style={styles.brand}>{product.brand}</Text>
            
            <Text style={styles.reason} numberOfLines={2}>
              {item.reason}
            </Text>
            
            <View style={styles.priceRow}>
              <Text style={styles.price}>
                {parseFloat(product.price).toLocaleString('tr-TR', {
                  style: 'currency',
                  currency: 'TRY',
                })}
              </Text>
              <View
                style={[
                  styles.stockBadge,
                  { backgroundColor: isInStock ? '#4CAF50' : '#f44336' },
                ]}
              >
                <Text style={styles.stockText}>
                  {isInStock ? 'Stokta' : 'Stok Yok'}
                </Text>
              </View>
            </View>
          </View>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.wishlistButton}
            onPress={() => handleAddToWishlist(product.id, product.name)}
          >
            <FontAwesome name="heart-o" size={18} color="#f44336" />
            <Text style={styles.wishlistButtonText}>İstek Listesine Ekle</Text>
          </TouchableOpacity>
        </View>
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#000000" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={recommendations}
        renderItem={renderItem}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <View>
              <Text style={styles.headerTitle}>Size Özel Öneriler</Text>
              <Text style={styles.subtitle}>
                Görüntüleme geçmişinize göre seçildi
              </Text>
            </View>
            <TouchableOpacity
              style={[styles.generateButton, generating && styles.disabledButton]}
              onPress={handleGenerateRecommendations}
              disabled={generating}
            >
              {generating ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <FontAwesome name="refresh" size={14} color="#fff" />
                  <Text style={styles.generateButtonText}>Yenile</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <FontAwesome name="lightbulb-o" size={80} color="#ccc" />
            <Text style={styles.emptyTitle}>Henüz Öneri Yok</Text>
            <Text style={styles.emptyText}>
              Ürünleri görüntüledikçe size özel öneriler burada görünecek
            </Text>
            <TouchableOpacity
              style={styles.browseButton}
              onPress={handleGenerateRecommendations}
            >
              <Text style={styles.browseButtonText}>Öneri Oluştur</Text>
            </TouchableOpacity>
          </View>
        }
      />
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
  subtitle: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  generateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#9C27B0',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  generateButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 13,
  },
  disabledButton: {
    opacity: 0.6,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    overflow: 'hidden',
  },
  clickedCard: {
    opacity: 0.8,
  },
  scoreBadge: {
    position: 'absolute',
    top: 10,
    right: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    zIndex: 1,
  },
  scoreText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: 'bold',
  },
  cardContent: {
    flexDirection: 'row',
    padding: 12,
  },
  image: {
    width: 100,
    height: 100,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
  },
  imagePlaceholder: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  info: {
    flex: 1,
    marginLeft: 12,
  },
  productName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  // 🆕 ADDED: Style for Category
  categoryText: {
    fontSize: 12,
    color: '#0288D1',
    fontWeight: '500',
    marginTop: 2,
  },
  brand: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  reason: {
    fontSize: 12,
    color: '#9C27B0',
    fontStyle: 'italic',
    marginTop: 6,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  price: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#000000',
  },
  stockBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  stockText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '600',
  },
  actions: {
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    padding: 12,
  },
  wishlistButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    gap: 8,
  },
  wishlistButtonText: {
    color: '#f44336',
    fontWeight: '600',
    fontSize: 14,
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
    paddingHorizontal: 40,
  },
  browseButton: {
    marginTop: 20,
    backgroundColor: '#9C27B0',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  browseButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
});

export default RecommendationsScreen;