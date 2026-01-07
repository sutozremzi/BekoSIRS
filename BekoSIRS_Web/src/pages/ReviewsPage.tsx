import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import { Star, Search, Filter, CheckCircle, XCircle, Clock } from "lucide-react";
import api from "../services/api";

interface Review {
  id: number;
  customer: number;
  customer_name: string;
  product: number;
  product_name: string;
  rating: number;
  comment: string;
  created_at: string;
  updated_at: string;
  is_approved: boolean;
}

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("Tümü");
  const [ratingFilter, setRatingFilter] = useState("Tümü");

  useEffect(() => {
    fetchReviews();
  }, []);

  const fetchReviews = async () => {
    try {
      const response = await api.get("/reviews/");
      setReviews(Array.isArray(response.data) ? response.data : response.data.results || []);
    } catch (err: any) {
      setError(err.message || "Değerlendirmeler yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (reviewId: number) => {
    try {
      await api.post(`/reviews/${reviewId}/approve/`);
      fetchReviews();
    } catch (err: any) {
      alert(err.message || "Onaylama başarısız");
    }
  };

  const handleDelete = async (reviewId: number) => {
    if (!window.confirm("Bu değerlendirmeyi silmek istediğinize emin misiniz?")) return;

    try {
      await api.delete(`/reviews/${reviewId}/`);
      fetchReviews();
    } catch (err: any) {
      alert(err.message || "Silme başarısız");
    }
  };

  const filteredReviews = reviews.filter((review) => {
    const matchesSearch =
      review.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      review.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      review.comment?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === "Tümü" ||
      (statusFilter === "approved" && review.is_approved) ||
      (statusFilter === "pending" && !review.is_approved);

    const matchesRating = ratingFilter === "Tümü" || review.rating === Number(ratingFilter);

    return matchesSearch && matchesStatus && matchesRating;
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  const renderStars = (rating: number) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            size={16}
            className={star <= rating ? "text-yellow-400 fill-yellow-400" : "text-gray-300"}
          />
        ))}
      </div>
    );
  };

  const averageRating = reviews.length > 0
    ? (reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length).toFixed(1)
    : "0.0";

  const pendingCount = reviews.filter((r) => !r.is_approved).length;
  const approvedCount = reviews.filter((r) => r.is_approved).length;

  return (
    <div className="flex bg-gray-50 min-h-screen">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Star size={28} className="text-yellow-500" />
                <h1 className="text-2xl font-bold text-gray-900">Ürün Değerlendirmeleri</h1>
              </div>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <div className="bg-gradient-to-br from-yellow-600 via-yellow-500 to-orange-500 text-white">
          <div className="max-w-7xl mx-auto px-6 py-12">
            <h2 className="text-3xl font-bold mb-2">Değerlendirme Yönetimi</h2>
            <p className="text-yellow-100">Müşteri yorumlarını inceleyin ve onaylayın</p>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <p className="text-yellow-100 text-sm">Toplam</p>
                <p className="text-2xl font-bold mt-1">{reviews.length}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <p className="text-yellow-100 text-sm">Onaylı</p>
                <p className="text-2xl font-bold mt-1">{approvedCount}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <p className="text-yellow-100 text-sm">Bekleyen</p>
                <p className="text-2xl font-bold mt-1">{pendingCount}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <p className="text-yellow-100 text-sm">Ortalama Puan</p>
                <div className="flex items-center gap-2 mt-1">
                  <Star size={20} className="fill-white" />
                  <p className="text-2xl font-bold">{averageRating}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto w-full px-6 py-8">
          {/* Filters */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-8 flex flex-col md:flex-row md:items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Değerlendirme ara..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-yellow-500"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Filter size={20} className="text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-yellow-500 cursor-pointer bg-white"
              >
                <option value="Tümü">Tüm Durumlar</option>
                <option value="approved">Onaylı</option>
                <option value="pending">Bekleyen</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <Star size={20} className="text-gray-400" />
              <select
                value={ratingFilter}
                onChange={(e) => setRatingFilter(e.target.value)}
                className="px-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-yellow-500 cursor-pointer bg-white"
              >
                <option value="Tümü">Tüm Puanlar</option>
                {[5, 4, 3, 2, 1].map((r) => (
                  <option key={r} value={r}>{r} Yıldız</option>
                ))}
              </select>
            </div>
          </div>

          {/* Reviews Grid */}
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500 mx-auto"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl">{error}</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredReviews.map((review) => (
                <div
                  key={review.id}
                  className={`bg-white rounded-2xl shadow-sm border overflow-hidden ${review.is_approved ? "border-green-200" : "border-orange-200"
                    }`}
                >
                  <div className="p-6">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <p className="font-semibold text-gray-900">{review.customer_name}</p>
                        <p className="text-sm text-gray-500">{review.product_name}</p>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${review.is_approved
                          ? "bg-green-100 text-green-600"
                          : "bg-orange-100 text-orange-600"
                          }`}
                      >
                        {review.is_approved ? "Onaylı" : "Bekliyor"}
                      </span>
                    </div>

                    {/* Rating */}
                    <div className="mb-3">{renderStars(review.rating)}</div>

                    {/* Comment */}
                    <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                      {review.comment || "Yorum yapılmamış"}
                    </p>

                    {/* Date */}
                    <p className="text-xs text-gray-400 mb-4">{formatDate(review.created_at)}</p>

                    {/* Actions */}
                    <div className="flex gap-2 pt-4 border-t">
                      {!review.is_approved && (
                        <button
                          onClick={() => handleApprove(review.id)}
                          className="flex-1 bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 flex items-center justify-center gap-1"
                        >
                          <CheckCircle size={16} />
                          Onayla
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(review.id)}
                        className="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 flex items-center justify-center gap-1"
                      >
                        <XCircle size={16} />
                        Sil
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {filteredReviews.length === 0 && !loading && !error && (
            <div className="text-center py-12 text-gray-500">
              Değerlendirme bulunamadı
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
