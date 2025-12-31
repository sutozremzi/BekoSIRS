import React, { useEffect, useState, useMemo } from "react";
import * as Lucide from "lucide-react";
import Sidebar from "../components/Sidebar";
import Drawer from "../components/Drawer";
import ConfirmDialog from "../components/ConfirmDialog";
import { ToastContainer, type ToastType } from "../components/Toast";

// Safe Icon Imports with fallbacks
const {
  Package = () => <span>📦</span>,
  Plus = () => <span>+</span>,
  Search = () => <span>🔍</span>,
  Filter = () => <span>⚡</span>,
  MoreVertical = () => <span>⋮</span>,
  Edit2 = () => <span>✎</span>,
  Trash2 = () => <span>🗑</span>,
  Copy = () => <span>❐</span>,
  Power = () => <span>⏻</span>,
  PowerOff = () => <span>○</span>,
  DollarSign = () => <span>$</span>,
  X = () => <span>✕</span>,
  ChevronDown = () => <span>▼</span>,
  ChevronUp = () => <span>▲</span>,
  FileSpreadsheet = () => <span>📊</span>,
  Download = () => <span>⬇</span>,
  LayoutGrid = () => <span>▦</span>,
  List = () => <span>≡</span>,
  Loader2 = () => <span>↻</span>,
  Eye = () => <span>O</span>
} = Lucide as any;

interface Product {
  id: number;
  name: string;
  brand: string;
  category: { id: number; name: string } | null;
  price: string;
  stock: number;
  warranty_duration_months: number;
  description?: string;
  image?: string;
}

interface Category {
  id: number;
  name: string;
}

type DensityMode = 'compact' | 'normal' | 'comfortable';
type SavedView = 'all' | 'out_of_stock' | 'low_stock' | 'recent';

export default function ProductsPage() {
  // Core Data
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [priceMin, setPriceMin] = useState<string>("");
  const [priceMax, setPriceMax] = useState<string>("");
  const [stockFilter, setStockFilter] = useState<string>("all");
  const [activeView, setActiveView] = useState<SavedView>("all");

  // Table State
  const [sortBy, setSortBy] = useState<{ field: string; direction: 'asc' | 'desc' }>({ field: 'name', direction: 'asc' });
  const [density, setDensity] = useState<DensityMode>('normal');
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);

  // UI State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [viewingProduct, setViewingProduct] = useState<Product | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{ open: boolean; action: () => void; title: string; message: string }>({ open: false, action: () => { }, title: '', message: '' });
  const [toasts, setToasts] = useState<Array<{ id: string; type: ToastType; message: string }>>([]);
  const [openDropdown, setOpenDropdown] = useState<number | null>(null);

  const token = localStorage.getItem("access");

  useEffect(() => {
    fetchProducts();
    fetchCategories();
  }, []);

  // Fetch Functions
  const fetchProducts = async () => {
    try {
      setLoading(true);
      const res = await fetch("http://127.0.0.1:8000/api/products/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch products");
      const data = await res.json();
      setProducts(Array.isArray(data) ? data : []);
    } catch (error: any) {
      showToast('error', 'Ürünler yüklenemedi: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/categories/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCategories(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error("Categories fetch failed", error);
    }
  };

  // Toast Functions
  const showToast = (type: ToastType, message: string) => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, type, message }]);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // Filter & Sort Logic
  const filteredAndSortedProducts = useMemo(() => {
    if (!Array.isArray(products)) return [];

    let filtered = [...products];

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(p =>
        (p.name || '').toLowerCase().includes(term) ||
        (p.brand || '').toLowerCase().includes(term) ||
        (p.category?.name || '').toLowerCase().includes(term)
      );
    }

    // Category filter
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(p => p.category?.id.toString() === selectedCategory);
    }

    // Price filter
    if (priceMin) {
      filtered = filtered.filter(p => parseFloat(p.price || '0') >= parseFloat(priceMin));
    }
    if (priceMax) {
      filtered = filtered.filter(p => parseFloat(p.price || '0') <= parseFloat(priceMax));
    }

    // Stock filter
    if (stockFilter === 'in_stock') {
      filtered = filtered.filter(p => p.stock > 0);
    } else if (stockFilter === 'out_of_stock') {
      filtered = filtered.filter(p => p.stock === 0);
    } else if (stockFilter === 'low_stock') {
      filtered = filtered.filter(p => p.stock > 0 && p.stock < 10);
    }

    // Sorting
    filtered.sort((a, b) => {
      let aVal: any = a[sortBy.field as keyof Product];
      let bVal: any = b[sortBy.field as keyof Product];

      if (sortBy.field === 'category') {
        aVal = a.category?.name || '';
        bVal = b.category?.name || '';
      }

      if (sortBy.field === 'price' || sortBy.field === 'stock') {
        aVal = parseFloat(aVal || '0') || 0;
        bVal = parseFloat(bVal || '0') || 0;
      }

      if (aVal < bVal) return sortBy.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortBy.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [products, searchTerm, selectedCategory, priceMin, priceMax, stockFilter, sortBy]);

  // Pagination
  const paginatedProducts = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredAndSortedProducts.slice(start, start + itemsPerPage);
  }, [filteredAndSortedProducts, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredAndSortedProducts.length / itemsPerPage);

  // KPIs
  const kpis = useMemo(() => {
    if (!Array.isArray(products)) return { total: 0, outOfStock: 0, lowStock: 0, totalValue: 0 };
    return {
      total: products.length,
      outOfStock: products.filter(p => p.stock === 0).length,
      lowStock: products.filter(p => p.stock > 0 && p.stock < 10).length,
      totalValue: products.reduce((sum, p) => sum + (parseFloat(p.price || '0') * (p.stock || 0)), 0),
    };
  }, [products]);

  // Saved Views
  const applySavedView = (view: SavedView) => {
    setActiveView(view);
    clearFilters();

    switch (view) {
      case 'out_of_stock':
        setStockFilter('out_of_stock');
        break;
      case 'low_stock':
        setStockFilter('low_stock');
        break;
      case 'recent':
        setSortBy({ field: 'id', direction: 'desc' });
        break;
    }
  };

  const clearFilters = () => {
    setSearchTerm("");
    setSelectedCategory("all");
    setPriceMin("");
    setPriceMax("");
    setStockFilter("all");
    setActiveView("all");
  };

  // Table Actions
  const handleSort = (field: string) => {
    setSortBy(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const toggleRowSelection = (id: number) => {
    setSelectedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const toggleAllRows = () => {
    if (selectedRows.size === paginatedProducts.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(paginatedProducts.map(p => p.id)));
    }
  };

  // CRUD Operations
  const handleEdit = (product: Product) => {
    setEditingProduct(product);
    setDrawerOpen(true);
    setOpenDropdown(null);
  };

  const handleDelete = (product: Product) => {
    setConfirmDialog({
      open: true,
      title: 'Ürünü Sil',
      message: `"${product.name}" ürününü silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.`,
      action: async () => {
        try {
          const res = await fetch(`http://127.0.0.1:8000/api/products/${product.id}/`, {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok || res.status === 204) {
            showToast('success', 'Ürün başarıyla silindi');
            await fetchProducts();
          } else {
            throw new Error("Silme işlemi başarısız");
          }
        } catch (error: any) {
          showToast('error', 'Ürün silinemedi: ' + error.message);
        }
      }
    });
    setOpenDropdown(null);
  };

  const handleSaveProduct = async (formData: Partial<Product>) => {
    try {
      const isNew = !editingProduct?.id;
      const url = isNew
        ? "http://127.0.0.1:8000/api/products/"
        : `http://127.0.0.1:8000/api/products/${editingProduct.id}/`;

      const res = await fetch(url, {
        method: isNew ? "POST" : "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!res.ok) throw new Error("Kaydetme başarısız");

      showToast('success', isNew ? 'Ürün başarıyla eklendi' : 'Ürün başarıyla güncellendi');
      setDrawerOpen(false);
      setEditingProduct(null);
      await fetchProducts();
    } catch (error: any) {
      showToast('error', 'Hata: ' + error.message);
    }
  };

  // Bulk Actions
  const handleBulkDelete = () => {
    setConfirmDialog({
      open: true,
      title: 'Toplu Silme',
      message: `${selectedRows.size} ürünü silmek istediğinizden emin misiniz?`,
      action: async () => {
        let successCount = 0;
        for (const id of selectedRows) {
          try {
            const res = await fetch(`http://127.0.0.1:8000/api/products/${id}/`, {
              method: "DELETE",
              headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok || res.status === 204) successCount++;
          } catch (error) {
            console.error(`Failed to delete product ${id}`);
          }
        }
        showToast('success', `${successCount} ürün silindi`);
        setSelectedRows(new Set());
        await fetchProducts();
      }
    });
  };

  // Density styles
  const densityPadding = {
    compact: 'py-2',
    normal: 'py-3',
    comfortable: 'py-4'
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
          <div className="px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Package />
              <h1 className="text-2xl font-bold text-gray-900">Ürün Yönetimi</h1>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => showToast('info', 'Excel import özelliği yakında eklenecek')}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <FileSpreadsheet />
                Excel İçe Aktar
              </button>
              <button
                onClick={() => {
                  setEditingProduct(null);
                  setDrawerOpen(true);
                }}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
              >
                <Plus />
                Ürün Ekle
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-[1600px] mx-auto space-y-6">

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div
                onClick={() => applySavedView('all')}
                className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
              >
                <p className="text-sm text-gray-600 mb-1">Toplam Ürün</p>
                <p className="text-3xl font-bold text-gray-900">{kpis.total}</p>
              </div>
              <div
                onClick={() => applySavedView('out_of_stock')}
                className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
              >
                <p className="text-sm text-gray-600 mb-1">Stok Tükendi</p>
                <p className="text-3xl font-bold text-red-600">{kpis.outOfStock}</p>
              </div>
              <div
                onClick={() => applySavedView('low_stock')}
                className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
              >
                <p className="text-sm text-gray-600 mb-1">Düşük Stok</p>
                <p className="text-3xl font-bold text-yellow-600">{kpis.lowStock}</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <p className="text-sm text-gray-600 mb-1">Toplam Değer</p>
                <p className="text-3xl font-bold text-green-600">{kpis.totalValue.toLocaleString('tr-TR')}₺</p>
              </div>
            </div>

            {/* Saved Views */}
            <div className="flex gap-2 flex-wrap">
              {[
                { id: 'all', label: 'Tüm Ürünler' },
                { id: 'out_of_stock', label: 'Stok Tükenenler' },
                { id: 'low_stock', label: 'Düşük Stok' },
                { id: 'recent', label: 'Son Eklenenler' },
              ].map(view => (
                <button
                  key={view.id}
                  onClick={() => applySavedView(view.id as SavedView)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeView === view.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                >
                  {view.label}
                </button>
              ))}
            </div>

            {/* Filters Bar */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                {/* Search */}
                <div className="md:col-span-2 relative">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                    <Search />
                  </div>
                  <input
                    type="text"
                    placeholder="Ürün, marka veya kategori ara..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>

                {/* Category */}
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="all">Tüm Kategoriler</option>
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>

                {/* Price Min */}
                <input
                  type="number"
                  placeholder="Min Fiyat"
                  value={priceMin}
                  onChange={(e) => setPriceMin(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                />

                {/* Price Max */}
                <input
                  type="number"
                  placeholder="Max Fiyat"
                  value={priceMax}
                  onChange={(e) => setPriceMax(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200">
                <div className="flex gap-2">
                  {['all', 'in_stock', 'out_of_stock', 'low_stock'].map(filter => (
                    <button
                      key={filter}
                      onClick={() => setStockFilter(filter)}
                      className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${stockFilter === filter
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                    >
                      {filter === 'all' ? 'Tümü' : filter === 'in_stock' ? 'Stokta' : filter === 'out_of_stock' ? 'Tükendi' : 'Düşük'}
                    </button>
                  ))}
                </div>

                {(searchTerm || selectedCategory !== 'all' || priceMin || priceMax || stockFilter !== 'all') && (
                  <button
                    onClick={clearFilters}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                  >
                    <X />
                    Filtreleri Temizle
                  </button>
                )}
              </div>
            </div>

            {/* Bulk Actions Toolbar */}
            {selectedRows.size > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 flex items-center justify-between">
                <span className="text-sm font-medium text-blue-900">
                  {selectedRows.size} ürün seçildi
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={handleBulkDelete}
                    className="px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium flex items-center gap-1"
                  >
                    <Trash2 />
                    Seçilenleri Sil
                  </button>
                  <button
                    onClick={() => setSelectedRows(new Set())}
                    className="px-3 py-1.5 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium"
                  >
                    İptal
                  </button>
                </div>
              </div>
            )}

            {/* Table */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {/* Table Header Controls */}
              <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <span className="text-sm text-gray-600">
                  {filteredAndSortedProducts.length} ürün gösteriliyor
                </span>
                <div className="flex items-center gap-2">
                  <select
                    value={itemsPerPage}
                    onChange={(e) => {
                      setItemsPerPage(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="px-2 py-1 border border-gray-300 rounded text-sm"
                  >
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                  <div className="flex gap-1 border border-gray-300 rounded">
                    {(['compact', 'normal', 'comfortable'] as DensityMode[]).map((d) => (
                      <button
                        key={d}
                        onClick={() => setDensity(d)}
                        className={`px-2 py-1 text-xs ${density === d ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
                        title={d}
                      >
                        {d === 'compact' ? 'K' : d === 'normal' ? 'N' : 'R'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left w-12">
                        <input
                          type="checkbox"
                          checked={selectedRows.size === paginatedProducts.length && paginatedProducts.length > 0}
                          onChange={toggleAllRows}
                          className="w-4 h-4 rounded border-gray-300"
                        />
                      </th>
                      {[
                        { field: 'name', label: 'Ürün Adı' },
                        { field: 'category', label: 'Kategori' },
                        { field: 'price', label: 'Fiyat' },
                        { field: 'stock', label: 'Stok' },
                      ].map(col => (
                        <th
                          key={col.field}
                          onClick={() => handleSort(col.field)}
                          className="px-4 py-3 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-gray-100 select-none"
                        >
                          <div className="flex items-center gap-1">
                            {col.label}
                            {sortBy.field === col.field && (
                              sortBy.direction === 'asc' ? <ChevronUp /> : <ChevronDown />
                            )}
                          </div>
                        </th>
                      ))}
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">İşlemler</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {paginatedProducts.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-12 text-center text-gray-500">
                          <Package />
                          <p className="font-medium">Ürün bulunamadı</p>
                          <p className="text-sm mt-1">Filtreleri değiştirmeyi deneyin</p>
                        </td>
                      </tr>
                    ) : (
                      paginatedProducts.map((product) => (
                        <tr key={product.id} className="hover:bg-gray-50 transition-colors">
                          <td className={`px-4 ${densityPadding[density]}`}>
                            <input
                              type="checkbox"
                              checked={selectedRows.has(product.id)}
                              onChange={() => toggleRowSelection(product.id)}
                              className="w-4 h-4 rounded border-gray-300"
                            />
                          </td>
                          <td className={`px-4 ${densityPadding[density]}`}>
                            <div>
                              <p className="font-medium text-gray-900">{product.name}</p>
                              <p className="text-sm text-gray-500">{product.brand}</p>
                            </div>
                          </td>
                          <td className={`px-4 ${densityPadding[density]}`}>
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                              {product.category?.name || 'Kategorisiz'}
                            </span>
                          </td>
                          <td className={`px-4 ${densityPadding[density]} font-semibold text-gray-900`}>
                            {parseFloat(product.price || '0').toLocaleString('tr-TR')}₺
                          </td>
                          <td className={`px-4 ${densityPadding[density]}`}>
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${product.stock === 0 ? 'bg-red-100 text-red-700' :
                              product.stock < 10 ? 'bg-yellow-100 text-yellow-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                              {product.stock} adet
                            </span>
                          </td>
                          <td className={`px-4 ${densityPadding[density]} relative`}>
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => setViewingProduct(product)}
                                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                title="Detayları Gör"
                              >
                                <Eye />
                              </button>
                              <button
                                onClick={() => setOpenDropdown(openDropdown === product.id ? null : product.id)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                              >
                                <MoreVertical />
                              </button>
                            </div>

                            {/* Dropdown Menu */}
                            {openDropdown === product.id && (
                              <>
                                <div
                                  className="fixed inset-0 z-10"
                                  onClick={() => setOpenDropdown(null)}
                                />
                                <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1">
                                  <button
                                    onClick={() => handleEdit(product)}
                                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                                  >
                                    <Edit2 />
                                    Düzenle
                                  </button>
                                  <button
                                    onClick={() => {
                                      showToast('info', 'Fiyat güncelleme özelliği yakında eklenecek');
                                      setOpenDropdown(null);
                                    }}
                                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                                  >
                                    <DollarSign />
                                    Fiyat Güncelle
                                  </button>
                                  <button
                                    onClick={() => {
                                      showToast('info', 'Çoğaltma özelliği yakında eklenecek');
                                      setOpenDropdown(null);
                                    }}
                                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                                  >
                                    <Copy />
                                    Çoğalt
                                  </button>
                                  <div className="border-t border-gray-200 my-1" />
                                  <button
                                    onClick={() => handleDelete(product)}
                                    className="w-full px-4 py-2 text-left text-sm hover:bg-red-50 text-red-600 flex items-center gap-2"
                                  >
                                    <Trash2 />
                                    Sil
                                  </button>
                                </div>
                              </>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    Sayfa {currentPage} / {totalPages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                      Önceki
                    </button>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                      Sonraki
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Edit Drawer */}
      <Drawer
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setEditingProduct(null);
        }}
        title={editingProduct?.id ? "Ürünü Düzenle" : "Yeni Ürün Ekle"}
      >
        <ProductForm
          product={editingProduct}
          categories={categories}
          onSave={handleSaveProduct}
          onCancel={() => {
            setDrawerOpen(false);
            setEditingProduct(null);
          }}
        />
      </Drawer>

      {/* View Detail Drawer */}
      <Drawer
        open={!!viewingProduct}
        onClose={() => setViewingProduct(null)}
        title="Ürün Detayları"
      >
        {viewingProduct && (
          <div className="space-y-6">
            {viewingProduct.image && (
              <div className="aspect-video rounded-lg bg-gray-100 overflow-hidden border border-gray-200">
                <img
                  src={viewingProduct.image}
                  alt={viewingProduct.name}
                  className="w-full h-full object-cover"
                />
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Ürün Adı</label>
                <p className="text-lg font-medium text-gray-900">{viewingProduct.name}</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Marka</label>
                <div className="flex items-center gap-2">
                  <span className="p-1.5 bg-gray-100 rounded-lg">
                    <Package size={16} className="text-gray-500" />
                  </span>
                  <p className="font-medium text-gray-900">{viewingProduct.brand}</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Kategori</label>
                <div className="flex items-center gap-2">
                  <span className="p-1.5 bg-gray-100 rounded-lg">
                    <LayoutGrid size={16} className="text-gray-500" />
                  </span>
                  <p className="font-medium text-gray-900">{viewingProduct.category?.name || 'Kategorisiz'}</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Fiyat</label>
                <div className="flex items-center gap-2">
                  <span className="p-1.5 bg-green-50 rounded-lg">
                    <DollarSign size={16} className="text-green-600" />
                  </span>
                  <p className="font-medium text-green-700">{parseFloat(viewingProduct.price || '0').toLocaleString('tr-TR')} ₺</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Stok Durumu</label>
                <div className="flex items-center gap-2">
                  <span className={`p-1.5 rounded-lg ${viewingProduct.stock === 0 ? 'bg-red-50' : viewingProduct.stock < 10 ? 'bg-yellow-50' : 'bg-green-50'}`}>
                    <Package size={16} className={`${viewingProduct.stock === 0 ? 'text-red-600' : viewingProduct.stock < 10 ? 'text-yellow-600' : 'text-green-600'}`} />
                  </span>
                  <p className={`font-medium ${viewingProduct.stock === 0 ? 'text-red-700' : viewingProduct.stock < 10 ? 'text-yellow-700' : 'text-green-700'}`}>
                    {viewingProduct.stock} adet
                  </p>
                </div>
              </div>

              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Garanti Süresi</label>
                <div className="flex items-center gap-2">
                  <span className="p-1.5 bg-blue-50 rounded-lg">
                    <FileSpreadsheet size={16} className="text-blue-600" />
                  </span>
                  <p className="font-medium text-gray-900">{viewingProduct.warranty_duration_months} Ay</p>
                </div>
              </div>
            </div>

            {viewingProduct.description && (
              <div className="pt-4 border-t border-gray-100">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Açıklama</label>
                <div className="bg-gray-50 rounded-lg p-4 text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">
                  {viewingProduct.description}
                </div>
              </div>
            )}

            <div className="pt-6 border-t border-gray-100 flex justify-end">
              <button
                onClick={() => setViewingProduct(null)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium transition-colors"
              >
                Kapat
              </button>
            </div>
          </div>
        )}
      </Drawer>

      {/* Confirm Dialog */}
      <ConfirmDialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ ...confirmDialog, open: false })}
        onConfirm={confirmDialog.action}
        title={confirmDialog.title}
        message={confirmDialog.message}
        variant="danger"
      />
    </div>
  );
}

// Product Form Component
interface ProductFormProps {
  product: Product | null;
  categories: Category[];
  onSave: (data: Partial<Product>) => void;
  onCancel: () => void;
}

function ProductForm({ product, categories, onSave, onCancel }: ProductFormProps) {
  const [formData, setFormData] = useState({
    name: product?.name || '',
    brand: product?.brand || '',
    category: product?.category?.id || '',
    price: product?.price || '',
    stock: product?.stock || 0,
    warranty_duration_months: product?.warranty_duration_months || 24,
    description: product?.description || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...formData,
      category: formData.category ? parseInt(formData.category as any) : null,
    } as any);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Ürün Adı *</label>
        <input
          type="text"
          required
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Marka *</label>
        <input
          type="text"
          required
          value={formData.brand}
          onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Kategori</label>
        <select
          value={formData.category}
          onChange={(e) => setFormData({ ...formData, category: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
        >
          <option value="">Kategori Seç</option>
          {categories.map(cat => (
            <option key={cat.id} value={cat.id}>{cat.name}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Fiyat (₺) *</label>
          <input
            type="number"
            required
            step="0.01"
            min="0"
            value={formData.price}
            onChange={(e) => setFormData({ ...formData, price: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Stok Adedi *</label>
          <input
            type="number"
            required
            min="0"
            value={formData.stock}
            onChange={(e) => setFormData({ ...formData, stock: parseInt(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Garanti (Ay)</label>
        <input
          type="number"
          min="0"
          value={formData.warranty_duration_months}
          onChange={(e) => setFormData({ ...formData, warranty_duration_months: parseInt(e.target.value) })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Açıklama</label>
        <textarea
          rows={4}
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none"
        />
      </div>

      <div className="flex gap-3 pt-4 border-t border-gray-200">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium"
        >
          İptal
        </button>
        <button
          type="submit"
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Kaydet
        </button>
      </div>
    </form>
  );
}