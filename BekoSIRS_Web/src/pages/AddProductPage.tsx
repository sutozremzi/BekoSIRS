import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { Package, Upload, X, ArrowLeft, Save } from "lucide-react";
import api from "../services/api";

export default function AddProductPage() {
  const navigate = useNavigate();

  // 1. State'e 'stock' alanını ekledik
  const [formData, setFormData] = useState({
    name: "",
    brand: "",
    category: "",
    price: "",
    stock: "", // Yeni alan: Stok Adedi
    warranty_duration_months: "",
    description: "",
    image: null as File | null,
  });

  const [categories, setCategories] = useState<any[]>([]);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);

  const token = localStorage.getItem("access");

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await api.get("/categories/");
        setCategories(Array.isArray(response.data) ? response.data : response.data.results || []);
      } catch (error) {
        console.error("Kategoriler çekilemedi:", error);
      } finally {
        setFetchLoading(false);
      }
    };

    fetchCategories();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFormData({ ...formData, image: file });
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setFormData({ ...formData, image: null });
    setImagePreview(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const form = new FormData();
    Object.entries(formData).forEach(([key, value]) => {
      if (value !== null && value !== "") {
        form.append(key, value as any);
      }
    });

    try {
      await api.post("/products/", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      alert("✅ Ürün başarıyla eklendi!");
      navigate("/dashboard/products");
    } catch (error) {
      alert("❌ Ürün eklenirken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <ArrowLeft size={24} />
              </button>
              <div className="flex items-center space-x-3">
                <Package size={28} className="text-blue-500" />
                <h1 className="text-2xl font-bold text-gray-900">Yeni Ürün Ekle</h1>
              </div>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
          <div className="max-w-4xl mx-auto px-6 py-12">
            <p className="text-gray-400 text-sm font-medium mb-2 tracking-widest uppercase">Ürün Yönetimi</p>
            <h2 className="text-3xl font-bold mb-2">Yeni Beko Ürünü Ekleyin</h2>
            <p className="text-gray-300">Veritabanındaki kategorilerle uyumlu ürün kaydı yapın</p>
          </div>
        </div>

        <main className="max-w-4xl mx-auto w-full px-6 py-10 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            <form onSubmit={handleSubmit}>
              <div className="p-8 space-y-8">
                {/* Ürün Adı */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Ürün Adı *</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    placeholder="Örn: Beko No-Frost Buzdolabı"
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none transition-all"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Marka */}
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Marka *</label>
                    <input
                      type="text"
                      name="brand"
                      value={formData.brand}
                      onChange={handleChange}
                      required
                      placeholder="Beko"
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none"
                    />
                  </div>

                  {/* Kategori Seçimi */}
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Kategori *</label>
                    <select
                      name="category"
                      value={formData.category}
                      onChange={handleChange}
                      required
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none bg-white cursor-pointer"
                    >
                      <option value="">Kategori Seçin</option>
                      {fetchLoading ? (
                        <option disabled>Yükleniyor...</option>
                      ) : (
                        categories.map((cat) => (
                          <option key={cat.id} value={cat.id}>
                            {cat.name}
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                </div>

                {/* 2. DÜZENLEME: Fiyat, Stok ve Garanti (3 Sütunlu Grid) */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Fiyat */}
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Fiyat (₺) *</label>
                    <input
                      type="number"
                      name="price"
                      value={formData.price}
                      onChange={handleChange}
                      required
                      placeholder="0.00"
                      step="0.01"
                      min="0"
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none"
                    />
                  </div>

                  {/* YENİ ALAN: Stok Adedi */}
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Stok Adedi *</label>
                    <input
                      type="number"
                      name="stock"
                      value={formData.stock}
                      onChange={handleChange}
                      required
                      placeholder="0"
                      min="0"
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none"
                    />
                  </div>

                  {/* Garanti */}
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Garanti Süresi (Ay)</label>
                    <input
                      type="number"
                      name="warranty_duration_months"
                      value={formData.warranty_duration_months}
                      onChange={handleChange}
                      placeholder="12"
                      min="0"
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none"
                    />
                  </div>
                </div>

                {/* Açıklama */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Açıklama</label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    rows={4}
                    placeholder="Ürün teknik özelliklerini buraya yazın..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none resize-none"
                  />
                </div>

                {/* Görsel Yükleme */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Ürün Görseli</label>
                  {imagePreview ? (
                    <div className="relative w-full h-64 bg-gray-50 rounded-xl overflow-hidden border border-gray-200">
                      <img src={imagePreview} alt="Preview" className="w-full h-full object-contain" />
                      <button
                        type="button"
                        onClick={removeImage}
                        className="absolute top-3 right-3 bg-red-500 text-white p-2 rounded-full hover:bg-red-600 shadow-lg"
                      >
                        <X size={20} />
                      </button>
                    </div>
                  ) : (
                    <div className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-black transition-colors cursor-pointer bg-gray-50">
                      <input
                        type="file"
                        id="image-upload"
                        className="hidden"
                        accept="image/*"
                        onChange={handleImageChange}
                      />
                      <label htmlFor="image-upload" className="cursor-pointer">
                        <Upload size={48} className="mx-auto text-gray-400 mb-4" />
                        <p className="text-gray-700 font-medium">Görsel yüklemek için tıklayın</p>
                        <p className="text-xs text-gray-500 mt-1">PNG, JPG veya JPEG</p>
                      </label>
                    </div>
                  )}
                </div>
              </div>

              {/* Form Footer */}
              <div className="bg-gray-50 px-8 py-6 border-t border-gray-200 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => navigate("/dashboard")}
                  className="px-6 py-3 text-gray-600 font-bold hover:text-black transition-all"
                >
                  İptal
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="bg-black text-white px-10 py-3.5 rounded-full font-bold hover:bg-gray-800 transition-all flex items-center space-x-2 disabled:opacity-50"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <>
                      <Save size={20} />
                      <span>Ürünü Kaydet</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
}