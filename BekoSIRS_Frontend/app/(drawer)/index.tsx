import React, { useEffect, useState, useCallback } from 'react';
import {
  SafeAreaView,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  RefreshControl,
  ScrollView,
} from 'react-native';
import { FontAwesome } from '@expo/vector-icons';
import api, { wishlistAPI } from '../../services/api';
import { ProductCard } from '../../components/ProductCard';

interface Category {
  id: number;
  name: string;
}

interface Product {
  id: number;
  name: string;
  brand: string;
  price: string;
  stock: number;
  image?: string;
  category?: { id: number; name: string } | null;
  category_name?: string;
}

const HomeScreen = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [wishlistIds, setWishlistIds] = useState<Set<number>>(new Set());

  const fetchData = useCallback(async () => {
    try {
      const [productsRes, categoriesRes, wishlistRes] = await Promise.all([
        api.get('/api/products/?page_size=1000'),
        api.get('/api/categories/?page_size=1000'),
        wishlistAPI.getWishlist(),
      ]);
      const productsData = Array.isArray(productsRes.data) ? productsRes.data : productsRes.data.results || [];
      const categoriesData = Array.isArray(categoriesRes.data) ? categoriesRes.data : categoriesRes.data.results || [];

      if (wishlistRes.data && wishlistRes.data.items) {
        const ids = wishlistRes.data.items.map((item: any) => item.product.id);
        setWishlistIds(new Set(ids));
      }

      setProducts(productsData);
      setFilteredProducts(productsData);
      setCategories(categoriesData);
    } catch (error) {
      console.error('Veri yükleme hatası:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    filterProducts();
  }, [searchQuery, selectedCategory, products]);

  const filterProducts = () => {
    let result = [...products];

    // Kategori filtresi
    if (selectedCategory !== null) {
      result = result.filter((p) => p.category?.id === selectedCategory);
    }

    // Arama filtresi
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          p.brand.toLowerCase().includes(query)
      );
    }

    setFilteredProducts(result);
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    setSearchQuery('');
    setSelectedCategory(null);
    fetchData();
  }, [fetchData]);

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory(null);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#000000" />
      </View>
    );
  }

  /* Simplified Header Logic */
  const ListHeader = () => (
    <View style={styles.headerContainer}>
      <Text style={styles.title}>Keşfet</Text>
      {/* Removed Subtitle */}

      {/* Arama Kutusu */}
      <View style={styles.searchContainer}>
        <FontAwesome name="search" size={16} color="#9CA3AF" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Ürün veya marka ara..."
          placeholderTextColor="#9CA3AF"
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')} style={styles.clearButton}>
            <FontAwesome name="times-circle" size={16} color="#9CA3AF" />
          </TouchableOpacity>
        )}
      </View>

      {/* Kategori Filtreleri */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.categoryScroll}
        contentContainerStyle={styles.categoryContainer}
      >
        <TouchableOpacity
          style={[
            styles.categoryChip,
            selectedCategory === null && styles.categoryChipActive,
          ]}
          onPress={() => setSelectedCategory(null)}
        >
          <Text
            style={[
              styles.categoryChipText,
              selectedCategory === null && styles.categoryChipTextActive,
            ]}
          >
            Tümü
          </Text>
        </TouchableOpacity>
        {categories.map((cat) => (
          <TouchableOpacity
            key={cat.id}
            style={[
              styles.categoryChip,
              selectedCategory === cat.id && styles.categoryChipActive,
            ]}
            onPress={() => setSelectedCategory(cat.id)}
          >
            <Text
              style={[
                styles.categoryChipText,
                selectedCategory === cat.id && styles.categoryChipTextActive,
              ]}
            >
              {cat.name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Aktif Filtre Bilgisi */}
      {(searchQuery || selectedCategory !== null) && (
        <View style={styles.activeFilterContainer}>
          <Text style={styles.activeFilterText}>
            {selectedCategory !== null &&
              `Kategori: ${categories.find((c) => c.id === selectedCategory)?.name}`}
            {searchQuery && selectedCategory !== null && ' • '}
            {searchQuery && `Arama: "${searchQuery}"`}
          </Text>
          <TouchableOpacity onPress={clearFilters} style={styles.clearFiltersButton}>
            <Text style={styles.clearFiltersText}>Temizle</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={filteredProducts}
        renderItem={({ item }) => (
          <ProductCard
            product={item}
            initialInWishlist={wishlistIds.has(item.id)}
          />
        )}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        ListHeaderComponent={ListHeader}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#000']} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <FontAwesome name="search" size={60} color="#ccc" />
            <Text style={styles.emptyTitle}>Ürün Bulunamadı</Text>
            <Text style={styles.emptyText}>
              Arama kriterlerinize uygun ürün bulunamadı.
            </Text>
            <TouchableOpacity style={styles.clearButton2} onPress={clearFilters}>
              <Text style={styles.clearButton2Text}>Filtreleri Temizle</Text>
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
    backgroundColor: '#fff', // White background for cleaner look
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerContainer: {
    paddingTop: 10,
    paddingBottom: 15,
  },
  title: {
    fontSize: 28, // Large modern title
    fontWeight: '800',
    color: '#111827',
    marginBottom: 16,
    letterSpacing: -0.5,
  },
  /* Removed Subtitle style */
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f3f4f6', // Light gray bg
    borderRadius: 12,
    paddingHorizontal: 16,
    marginBottom: 20,
    height: 50,
    /* No border */
  },
  searchIcon: {
    marginRight: 12,
  },
  searchInput: {
    flex: 1,
    height: '100%',
    fontSize: 15,
    color: '#111827',
    fontWeight: '500',
  },
  clearButton: {
    padding: 8,
  },
  categoryScroll: {
    marginBottom: 10,
  },
  categoryContainer: {
    paddingRight: 16,
    gap: 8,
  },
  categoryChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 100, // Pill shape
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    /* Subtle shadow instead of strong border */
  },
  categoryChipActive: {
    backgroundColor: '#111827', // Black
    borderColor: '#111827',
  },
  categoryChipText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4B5563',
  },
  categoryChipTextActive: {
    color: '#FFFFFF',
  },
  activeFilterContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#F9FAFB',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
    marginTop: 5,
  },
  activeFilterText: {
    fontSize: 13,
    color: '#374151',
    flex: 1,
  },
  clearFiltersButton: {
    marginLeft: 10,
  },
  clearFiltersText: {
    fontSize: 13,
    color: '#EF4444',
    fontWeight: '600',
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 18,
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
  clearButton2: {
    marginTop: 20,
    backgroundColor: '#000000',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  clearButton2Text: {
    color: '#fff',
    fontWeight: '600',
  },
});

export default HomeScreen;
