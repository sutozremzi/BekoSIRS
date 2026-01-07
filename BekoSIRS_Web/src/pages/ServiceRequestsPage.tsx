import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import {
  Wrench,
  Search,
  Filter,
  Clock,
  CheckCircle,
  XCircle,
  Play,
  User,
  ChevronDown,
  AlertCircle,
} from "lucide-react";
import api from "../services/api";

interface ServiceRequest {
  id: number;
  customer: number;
  customer_name: string;
  product_name: string;
  request_type: string;
  status: string;
  description: string;
  created_at: string;
  updated_at: string;
  assigned_to: number | null;
  assigned_to_name: string | null;
  resolution_notes: string | null;
  queue_entry?: {
    queue_number: number;
    priority: number;
    estimated_wait_time: number;
  };
}

interface User {
  id: number;
  username: string;
  role: string;
}

const statusConfig: Record<string, { label: string; color: string; bgColor: string; icon: any }> = {
  pending: { label: "Beklemede", color: "text-orange-600", bgColor: "bg-orange-100", icon: Clock },
  in_queue: { label: "Sırada", color: "text-blue-600", bgColor: "bg-blue-100", icon: AlertCircle },
  in_progress: { label: "İşlemde", color: "text-purple-600", bgColor: "bg-purple-100", icon: Play },
  completed: { label: "Tamamlandı", color: "text-green-600", bgColor: "bg-green-100", icon: CheckCircle },
  cancelled: { label: "İptal", color: "text-red-600", bgColor: "bg-red-100", icon: XCircle },
};

const requestTypeLabels: Record<string, string> = {
  repair: "Tamir",
  maintenance: "Bakım",
  warranty: "Garanti",
  complaint: "Şikayet",
  other: "Diğer",
};

export default function ServiceRequestsPage() {
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("Tümü");
  const [selectedRequest, setSelectedRequest] = useState<ServiceRequest | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [assignUserId, setAssignUserId] = useState<number | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [requestsRes, usersRes] = await Promise.all([
        api.get("/service-requests/"),
        api.get("/users/"),
      ]);

      const requestsArray = Array.isArray(requestsRes.data) ? requestsRes.data : requestsRes.data.results || [];
      const usersArray = Array.isArray(usersRes.data) ? usersRes.data : usersRes.data.results || [];

      setRequests(requestsArray);
      setUsers(usersArray.filter((u: User) => u.role === "admin" || u.role === "seller"));
    } catch (err: any) {
      setError(err.message || "Veriler yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async () => {
    if (!selectedRequest || !assignUserId) return;

    try {
      await api.post(`/service-requests/${selectedRequest.id}/assign/`, { assigned_to: assignUserId });
      setShowModal(false);
      fetchData();
    } catch (err: any) {
      alert(err.message || "Atama başarısız");
    }
  };

  const handleComplete = async () => {
    if (!selectedRequest) return;

    try {
      await api.post(`/service-requests/${selectedRequest.id}/complete/`, { resolution_notes: resolutionNotes });
      setShowModal(false);
      setResolutionNotes("");
      fetchData();
    } catch (err: any) {
      alert(err.message || "Tamamlama başarısız");
    }
  };

  const filteredRequests = requests.filter((req) => {
    const matchesSearch =
      req.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      req.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      req.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "Tümü" || req.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="flex bg-gray-50 min-h-screen">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Wrench size={28} className="text-purple-500" />
                <h1 className="text-2xl font-bold text-gray-900">Servis Talepleri</h1>
              </div>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <div className="bg-gradient-to-br from-purple-900 via-purple-800 to-black text-white">
          <div className="max-w-7xl mx-auto px-6 py-12">
            <h2 className="text-3xl font-bold mb-2">Servis Yönetimi</h2>
            <p className="text-purple-200">Müşteri servis taleplerini yönetin ve takip edin</p>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-8">
              {Object.entries(statusConfig).map(([key, config]) => {
                const count = requests.filter((r) => r.status === key).length;
                return (
                  <div key={key} className="bg-white/10 backdrop-blur rounded-xl p-4">
                    <p className="text-purple-200 text-sm">{config.label}</p>
                    <p className="text-2xl font-bold mt-1">{count}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto w-full px-6 py-8">
          {/* Filters */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Talep ara..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Filter size={20} className="text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-purple-500 cursor-pointer bg-white"
              >
                <option value="Tümü">Tüm Durumlar</option>
                {Object.entries(statusConfig).map(([key, config]) => (
                  <option key={key} value={key}>
                    {config.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Requests Table */}
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl">{error}</div>
          ) : (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase">ID</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase">Müşteri</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase">Ürün</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase">Tür</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase">Durum</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase">Atanan</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase">Tarih</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase">İşlem</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredRequests.map((req) => {
                    const status = statusConfig[req.status] || statusConfig.pending;
                    const StatusIcon = status.icon;
                    return (
                      <tr key={req.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4">
                          <span className="font-bold text-purple-600">SR-{req.id}</span>
                        </td>
                        <td className="px-6 py-4">{req.customer_name}</td>
                        <td className="px-6 py-4">{req.product_name}</td>
                        <td className="px-6 py-4">
                          <span className="bg-gray-100 px-2 py-1 rounded text-sm">
                            {requestTypeLabels[req.request_type] || req.request_type}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`${status.bgColor} ${status.color} px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1 w-fit`}>
                            <StatusIcon size={14} />
                            {status.label}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {req.assigned_to_name || (
                            <span className="text-gray-400">Atanmadı</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">
                          {formatDate(req.created_at)}
                        </td>
                        <td className="px-6 py-4">
                          <button
                            onClick={() => {
                              setSelectedRequest(req);
                              setShowModal(true);
                            }}
                            className="text-purple-600 hover:text-purple-800 font-medium"
                          >
                            Detay
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {filteredRequests.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  Servis talebi bulunamadı
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Detail Modal */}
      {showModal && selectedRequest && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
          <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
            <div className="p-6 flex justify-between items-center border-b">
              <h2 className="text-2xl font-bold text-gray-900">
                SR-{selectedRequest.id} Detay
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <XCircle size={24} />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400 uppercase font-bold">Müşteri</p>
                  <p className="font-semibold">{selectedRequest.customer_name}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase font-bold">Ürün</p>
                  <p className="font-semibold">{selectedRequest.product_name}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase font-bold">Tür</p>
                  <p className="font-semibold">
                    {requestTypeLabels[selectedRequest.request_type]}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase font-bold">Durum</p>
                  <p className={`font-semibold ${statusConfig[selectedRequest.status]?.color}`}>
                    {statusConfig[selectedRequest.status]?.label}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-xs text-gray-400 uppercase font-bold mb-2">Açıklama</p>
                <p className="bg-gray-50 p-4 rounded-xl">{selectedRequest.description}</p>
              </div>

              {selectedRequest.queue_entry && (
                <div className="bg-blue-50 p-4 rounded-xl">
                  <p className="text-xs text-blue-600 uppercase font-bold mb-2">Kuyruk Bilgisi</p>
                  <div className="flex gap-4">
                    <div>
                      <span className="text-sm text-blue-600">Sıra No:</span>
                      <span className="font-bold ml-2">{selectedRequest.queue_entry.queue_number}</span>
                    </div>
                    <div>
                      <span className="text-sm text-blue-600">Tahmini Süre:</span>
                      <span className="font-bold ml-2">{selectedRequest.queue_entry.estimated_wait_time} dk</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Actions */}
              {selectedRequest.status !== "completed" && selectedRequest.status !== "cancelled" && (
                <div className="space-y-4 pt-4 border-t">
                  {/* Assign */}
                  {!selectedRequest.assigned_to && (
                    <div>
                      <p className="text-xs text-gray-400 uppercase font-bold mb-2">Personel Ata</p>
                      <div className="flex gap-2">
                        <select
                          value={assignUserId || ""}
                          onChange={(e) => setAssignUserId(Number(e.target.value))}
                          className="flex-1 px-4 py-2 border rounded-xl"
                        >
                          <option value="">Seçin...</option>
                          {users.map((u) => (
                            <option key={u.id} value={u.id}>
                              {u.username} ({u.role})
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={handleAssign}
                          className="bg-purple-600 text-white px-6 py-2 rounded-xl hover:bg-purple-700"
                        >
                          Ata
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Complete */}
                  {selectedRequest.status === "in_progress" && (
                    <div>
                      <p className="text-xs text-gray-400 uppercase font-bold mb-2">Tamamla</p>
                      <textarea
                        value={resolutionNotes}
                        onChange={(e) => setResolutionNotes(e.target.value)}
                        placeholder="Çözüm notları..."
                        className="w-full px-4 py-2 border rounded-xl mb-2"
                        rows={3}
                      />
                      <button
                        onClick={handleComplete}
                        className="bg-green-600 text-white px-6 py-2 rounded-xl hover:bg-green-700 w-full"
                      >
                        Talebi Tamamla
                      </button>
                    </div>
                  )}
                </div>
              )}

              {selectedRequest.resolution_notes && (
                <div className="bg-green-50 p-4 rounded-xl">
                  <p className="text-xs text-green-600 uppercase font-bold mb-2">Çözüm Notları</p>
                  <p>{selectedRequest.resolution_notes}</p>
                </div>
              )}
            </div>

            <div className="p-6 border-t bg-gray-50">
              <button
                onClick={() => setShowModal(false)}
                className="w-full bg-black text-white py-3 rounded-full font-bold hover:bg-gray-800"
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
