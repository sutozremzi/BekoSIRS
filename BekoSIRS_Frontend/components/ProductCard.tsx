// components/ProductCard.tsx

import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Image, TouchableOpacity, Alert } from 'react-native';
import { FontAwesome } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { wishlistAPI, viewHistoryAPI } from '../services/api';

interface ProductCardProps {
  product: {
    id: number;
    name: string;
    brand: string;
    price: string;
    image_url?: string;
    image?: string;
    stock?: number;
    category_name?: string;
  };
  onPress?: () => void;
  initialInWishlist?: boolean;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onPress, initialInWishlist = false }) => {
  const router = useRouter();
  const [inWishlist, setInWishlist] = useState(initialInWishlist);
  const [loading, setLoading] = useState(false);



  const imageSource = product.image_url || product.image;

  useEffect(() => {
    setInWishlist(initialInWishlist || false);
  }, [initialInWishlist]);

  const handleWishlistToggle = async () => {
    setLoading(true);
    try {
      if (inWishlist) {
        await wishlistAPI.removeItem(product.id);
        setInWishlist(false);
      } else {
        await wishlistAPI.addItem(product.id);
        setInWishlist(true);
      }
    } catch (error: any) {
      Alert.alert('Hata', error.response?.data?.error || 'İşlem başarısız');
    } finally {
      setLoading(false);
    }
  };

  const handlePress = async () => {
    // Record view when product is clicked
    try {
      await viewHistoryAPI.recordView(product.id);
    } catch (error) {
      // Ignore error
    }
    if (onPress) {
      onPress();
    } else {
      // Navigate to product detail page
      router.push(`/product/${product.id}`);
    }
  };

  const isInStock = (product.stock ?? 0) > 0;

  return (
    <TouchableOpacity onPress={handlePress} activeOpacity={0.8}>
      <View style={styles.card}>
        {imageSource && <Image source={{ uri: imageSource }} style={styles.image} />}

        {/* Wishlist Button */}
        <TouchableOpacity
          style={styles.wishlistButton}
          onPress={handleWishlistToggle}
          disabled={loading}
        >
          <FontAwesome
            name={inWishlist ? "heart" : "heart-o"}
            size={22}
            color={inWishlist ? "#f44336" : "#999"}
          />
        </TouchableOpacity>

        {/* Stock Badge */}
        {product.stock !== undefined && (
          <View style={[styles.stockBadge, { backgroundColor: isInStock ? '#4CAF50' : '#f44336' }]}>
            <Text style={styles.stockText}>
              {isInStock ? `Stokta` : 'Stok Yok'}
            </Text>
          </View>
        )}

        <View style={styles.infoContainer}>
          <Text style={styles.name} numberOfLines={2}>{product.name}</Text>
          <Text style={styles.brand}>{product.brand}</Text>
          {product.category_name && (
            <Text style={styles.category}>{product.category_name}</Text>
          )}
          <Text style={styles.price}>
            {parseFloat(product.price).toLocaleString('tr-TR', { style: 'currency', currency: 'TRY' })}
          </Text>
        </View>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: 'white',
    borderRadius: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
    overflow: 'hidden',
    position: 'relative',
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  image: {
    width: '100%',
    height: 180,
    backgroundColor: '#f9fafb',
  },
  wishlistButton: {
    position: 'absolute',
    top: 12,
    right: 12,
    backgroundColor: 'rgba(255,255,255,0.95)',
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  stockBadge: {
    position: 'absolute',
    top: 12,
    left: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    zIndex: 1,
  },
  stockText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
  infoContainer: {
    padding: 16,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
    lineHeight: 22,
  },
  brand: {
    fontSize: 13,
    color: '#6B7280',
    marginBottom: 4,
    fontWeight: '500',
  },
  category: {
    fontSize: 11,
    color: '#9CA3AF',
    marginBottom: 8,
    fontWeight: '500',
  },
  price: {
    fontSize: 18,
    fontWeight: '700',
    color: '#000000',
    textAlign: 'left', // Aligned left looks modern
  },
});