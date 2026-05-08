import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import { Star, Search, Filter, CheckCircle, XCircle, ChevronRight, X, MessageSquare, Trash2, User, Package } from "lucide-react";
import api from "../services/api";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();

  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [ratingFilter, setRatingFilter] = useState("all");

  // Detail Panel State
  const [selectedReview, setSelectedReview] = useState<Review | null>(null);
  const [showDetailPanel, setShowDetailPanel] = useState(false);

  useEffect(() => {
    fetchReviews();
  }, []);

  const fetchReviews = async () => {
    try {
      const response = await api.get("/reviews/");
      setReviews(Array.isArray(response.data) ? response.data : response.data.results || []);
    } catch (err: any) {
      setError(err.message || t('reviews.errFetch'));
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (reviewId: number) => {
    try {
      await api.post(`/reviews/${reviewId}/approve/`);
      // Update local state without fetching
      setReviews(prev => prev.map(r => r.id === reviewId ? { ...r, is_approved: true } : r));
      if (selectedReview && selectedReview.id === reviewId) {
        setSelectedReview(prev => prev ? { ...prev, is_approved: true } : null);
      }
    } catch (err: any) {
      alert(err.message || t('reviews.errApprove'));
    }
  };

  const handleDelete = async (reviewId: number) => {
    if (!window.confirm(t('reviews.confirmDelete'))) return;

    try {
      await api.delete(`/reviews/${reviewId}/`);
      // Remove from local state
      setReviews(prev => prev.filter(r => r.id !== reviewId));
      if (selectedReview?.id === reviewId) {
        setShowDetailPanel(false);
        setSelectedReview(null);
      }
    } catch (err: any) {
      alert(err.message || t('reviews.errDelete'));
    }
  };

  const openDetailPanel = (review: Review) => {
    setSelectedReview(review);
    setShowDetailPanel(true);
  };

  const filteredReviews = reviews.filter((review) => {
    const matchesSearch =
      review.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      review.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      review.comment?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "approved" && review.is_approved) ||
      (statusFilter === "pending" && !review.is_approved);

    const matchesRating = ratingFilter === "all" || review.rating === Number(ratingFilter);

    return matchesSearch && matchesStatus && matchesRating;
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const renderStars = (rating: number, size = 16) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            size={size}
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
                <h1 className="text-2xl font-bold text-gray-900">{t('reviews.title')}</h1>
              </div>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <div className="bg-gradient-to-br from-yellow-600 via-yellow-500 to-orange-500 text-white">
          <div className="max-w-7xl mx-auto px-6 py-12">
            <h2 className="text-3xl font-bold mb-2">{t('reviews.subtitle')}</h2>
            <p className="text-yellow-100">{t('reviews.desc')}</p>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <p className="text-yellow-100 text-sm">{t('reviews.statTotal')}</p>
                <p className="text-2xl font-bold mt-1">{reviews.length}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <p className="text-yellow-100 text-sm">{t('reviews.statApproved')}</p>
                <p className="text-2xl font-bold mt-1">{approvedCount}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <p className="text-yellow-100 text-sm">{t('reviews.statPending')}</p>
                <p className="text-2xl font-bold mt-1">{pendingCount}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <p className="text-yellow-100 text-sm">{t('reviews.statAvg')}</p>
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
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4 mb-8 flex flex-col md:flex-row md:items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder={t('reviews.searchPlaceholder')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-11 pr-4 py-2.5 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-yellow-500 text-sm"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Filter size={18} className="text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-2.5 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-yellow-500 cursor-pointer bg-white text-sm"
              >
                <option value="all">{t('reviews.filterStatusAll')}</option>
                <option value="approved">{t('reviews.filterStatusApproved')}</option>
                <option value="pending">{t('reviews.filterStatusPending')}</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <Star size={18} className="text-gray-400" />
              <select
                value={ratingFilter}
                onChange={(e) => setRatingFilter(e.target.value)}
                className="px-4 py-2.5 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-yellow-500 cursor-pointer bg-white text-sm"
              >
                <option value="all">{t('reviews.filterRatingAll')}</option>
                {[5, 4, 3, 2, 1].map((r) => (
                  <option key={r} value={r}>{t('reviews.filterRatingStars', { rating: r })}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Reviews Table */}
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500 mx-auto"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl">{error}</div>
          ) : (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{t('reviews.colCustomer')}</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{t('reviews.colProduct')}</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{t('reviews.colRating')}</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{t('reviews.colStatus')}</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{t('reviews.colDate')}</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-600 uppercase">{t('reviews.colAction')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredReviews.map((review) => (
                    <tr
                      key={review.id}
                      onClick={() => openDetailPanel(review)}
                      className="hover:bg-yellow-50 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900">{review.customer_name}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" title={review.product_name}>
                        {review.product_name}
                      </td>
                      <td className="px-6 py-4">
                        {renderStars(review.rating, 14)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${review.is_approved
                          ? "bg-green-100 text-green-700"
                          : "bg-orange-100 text-orange-700"
                          }`}>
                          {review.is_approved ? t('reviews.statusApproved') : t('reviews.statusPending')}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs text-gray-500">
                        {formatDate(review.created_at)}
                      </td>
                      <td className="px-6 py-4 text-right text-gray-400">
                        <div className="flex justify-end">
                          <ChevronRight size={18} />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredReviews.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  {t('reviews.noReviews')}
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Detail Slide-Over Panel */}
      {showDetailPanel && selectedReview && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 z-40 transition-opacity"
            onClick={() => setShowDetailPanel(false)}
          />

          {/* Drawer */}
          <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl z-50 flex flex-col transform transition-transform duration-300">
            {/* Header */}
            <div className="p-4 border-b flex justify-between items-center bg-yellow-500 text-white">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Star className="fill-white" size={20} />
                {t('reviews.modalTitle')}
              </h2>
              <button
                onClick={() => setShowDetailPanel(false)}
                className="p-2 hover:bg-yellow-600 rounded-full transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* User Info */}
              <div className="flex items-center gap-3 pb-4 border-b border-gray-100">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center text-gray-500">
                  <User size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-900">{selectedReview.customer_name}</h3>
                  <p className="text-sm text-gray-500">{formatDate(selectedReview.created_at)}</p>
                </div>
              </div>

              {/* Product Info */}
              <div className="bg-gray-50 p-4 rounded-xl flex items-center gap-3">
                <div className="bg-white p-2 rounded-lg border border-gray-200">
                  <Package size={20} className="text-blue-500" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase font-semibold">{t('reviews.lblProduct')}</p>
                  <p className="text-sm font-medium text-gray-900 line-clamp-2">{selectedReview.product_name}</p>
                </div>
              </div>

              {/* Rating & Comment */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-semibold text-gray-700">{t('reviews.lblRating')}</p>
                  {renderStars(selectedReview.rating, 20)}
                </div>
                <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                  <div className="flex items-start gap-2">
                    <MessageSquare size={16} className="text-gray-400 mt-1 shrink-0" />
                    <p className="text-gray-700 italic">"{selectedReview.comment || t('reviews.noComment')}"</p>
                  </div>
                </div>
              </div>

              {/* Approval Status */}
              <div className="flex items-center justify-between bg-gray-50 p-4 rounded-xl">
                <span className="text-sm font-medium text-gray-700">{t('reviews.lblStatus')}</span>
                <span className={`px-3 py-1 rounded-full text-sm font-bold ${selectedReview.is_approved
                    ? "bg-green-100 text-green-700"
                    : "bg-orange-100 text-orange-700"
                  }`}>
                  {selectedReview.is_approved ? t('reviews.statusApprovedLong') : t('reviews.statusPendingLong')}
                </span>
              </div>
            </div>

            {/* Actions Footer */}
            <div className="p-4 border-t border-gray-200 bg-gray-50 gap-3 flex">
              {!selectedReview.is_approved && (
                <button
                  onClick={() => handleApprove(selectedReview.id)}
                  className="flex-1 bg-green-600 text-white py-3 rounded-xl font-bold hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
                >
                  <CheckCircle size={20} />
                  {t('reviews.btnApprove')}
                </button>
              )}

              <button
                onClick={() => handleDelete(selectedReview.id)}
                className="flex-none bg-red-100 text-red-600 p-3 rounded-xl hover:bg-red-200 transition-colors"
                title={t('reviews.btnDelete')}
              >
                <Trash2 size={24} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
