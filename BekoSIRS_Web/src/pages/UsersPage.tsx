import React, { useEffect, useState } from "react";
import {
  Users,
  UserPlus,
  Crown,
  Store,
  UserCircle,
  Mail,
  Lock,
  User,
  Search,
  Filter,
  CheckCircle,
  XCircle,
} from "lucide-react";
import Sidebar from "../components/Sidebar";
import api from "../services/api";

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("Tümü");
  const [showAddModal, setShowAddModal] = useState(false);
  const [newUser, setNewUser] = useState({
    username: "",
    email: "",
    password: "",
    role: "customer",
  });

  const token = localStorage.getItem("access");

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const res = await api.get("/users/");
        setUsers(Array.isArray(res.data) ? res.data : res.data.results || []);
      } catch (err: any) {
        setError(err.message || "Kullanıcı listesi alınamadı.");
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const handleRoleChange = async (id: number, newRole: string) => {
    if (window.confirm(`Bu kullanıcının rolünü ${getRoleDisplayName(newRole)} olarak değiştirmek istediğinizden emin misiniz?`)) {
      try {
        await api.post(`/users/${id}/set_role/`, { role: newRole });
        setUsers((prev) =>
          prev.map((u) => (u.id === id ? { ...u, role: newRole } : u))
        );
      } catch (err: any) {
        setError(err.message || "Rol güncellenemedi.");
      }
    }
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post("/users/", newUser);
      setUsers((prev) => [...prev, res.data]);
      setNewUser({ username: "", email: "", password: "", role: "customer" });
      setShowAddModal(false);
      alert("✅ Kullanıcı başarıyla eklendi!");
    } catch (err: any) {
      setError(err.message || "Kullanıcı eklenemedi.");
    }
  };

  const filteredUsers = users.filter((user) => {
    const matchesSearch =
      user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = roleFilter === "Tümü" || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "admin":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      case "seller":
        return "bg-green-100 text-green-800 border-green-300";
      case "customer":
        return "bg-blue-100 text-blue-800 border-blue-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const getRoleDisplayName = (role: string) => {
    switch (role) {
      case "admin": return "Admin";
      case "seller": return "Satıcı";
      case "customer": return "Müşteri";
      default: return role;
    }
  };

  const roleStats = {
    total: users.length,
    admin: users.filter((u) => u.role === "admin").length,
    seller: users.filter((u) => u.role === "seller").length,
    customer: users.filter((u) => u.role === "customer").length,
    active: users.filter((u) => u.is_active).length,
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-black mx-auto"></div>
            <p className="text-gray-600 mt-4 text-lg">Kullanıcılar yükleniyor...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Users size={28} className="text-blue-500" />
                <h1 className="text-2xl font-bold text-gray-900">Kullanıcı Yönetimi</h1>
              </div>
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-black text-white px-6 py-2.5 rounded-full hover:bg-gray-800 transition-all font-medium flex items-center space-x-2"
              >
                <UserPlus size={20} />
                <span>Yeni Kullanıcı</span>
              </button>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
          <div className="max-w-7xl mx-auto px-6 py-12">
            <p className="text-gray-400 text-sm font-medium mb-2">YÖNETİM PANELİ</p>
            <h2 className="text-3xl font-bold mb-2">Kullanıcıları Yönetin</h2>
            <p className="text-gray-300">Kullanıcı ekleyin, rollerini düzenleyin ve hesapları yönetin</p>
          </div>
        </div>

        <main className="max-w-7xl mx-auto w-full px-6 py-8 overflow-y-auto">
          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <Users size={24} className="text-gray-600" />
                <span className="text-2xl font-bold text-gray-900">{roleStats.total}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">Toplam</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <Crown size={24} className="text-yellow-500" />
                <span className="text-2xl font-bold text-yellow-600">{roleStats.admin}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">Admin</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <Store size={24} className="text-green-500" />
                <span className="text-2xl font-bold text-green-600">{roleStats.seller}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">Satıcı</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <UserCircle size={24} className="text-blue-500" />
                <span className="text-2xl font-bold text-blue-600">{roleStats.customer}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">Müşteri</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <CheckCircle size={24} className="text-emerald-500" />
                <span className="text-2xl font-bold text-emerald-600">{roleStats.active}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">Aktif</p>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-8">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Kullanıcı ara..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                />
              </div>

              <div className="flex items-center space-x-2">
                <Filter size={20} className="text-gray-400" />
                <select
                  value={roleFilter}
                  onChange={(e) => setRoleFilter(e.target.value)}
                  className="px-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-black cursor-pointer bg-white"
                >
                  <option value="Tümü">Tüm Roller</option>
                  <option value="admin">Admin</option>
                  <option value="seller">Satıcı</option>
                  <option value="customer">Müşteri</option>
                </select>
              </div>
            </div>
          </div>

          {/* Users Table */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">ID</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Kullanıcı</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">E-posta</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Rol</th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">Durum</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredUsers.length > 0 ? (
                    filteredUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">#{u.id}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                              <span className="text-white font-bold text-sm">
                                {u.username.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <span className="font-medium text-gray-900">{u.username}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">{u.email}</td>
                        <td className="px-6 py-4">
                          <select
                            value={u.role}
                            onChange={(e) => handleRoleChange(u.id, e.target.value)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-semibold border cursor-pointer transition-all ${getRoleBadgeColor(u.role)}`}
                          >
                            <option value="admin">⚙️ Admin</option>
                            <option value="seller">🏪 Satıcı</option>
                            <option value="customer">👤 Müşteri</option>
                          </select>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <div className="flex items-center justify-center space-x-2">
                            {u.is_active ? (
                              <><CheckCircle size={18} className="text-green-600" /><span className="text-sm font-semibold text-green-700">Aktif</span></>
                            ) : (
                              <><XCircle size={18} className="text-red-600" /><span className="text-sm font-semibold text-red-700">Pasif</span></>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-6 py-16 text-center">
                        <Users size={48} className="mx-auto text-gray-300 mb-3" />
                        <p className="text-gray-600 font-medium">Kullanıcı bulunamadı</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full">
            <div className="border-b border-gray-200 px-6 py-4">
              <h2 className="text-2xl font-bold flex items-center space-x-2">
                <UserPlus size={24} />
                <span>Yeni Kullanıcı Ekle</span>
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Kullanıcı Adı *</label>
                  <div className="relative">
                    <User className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                    <input type="text" value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none" placeholder="kullaniciadi" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">E-posta *</label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                    <input type="email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none" placeholder="ornek@email.com" />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Şifre *</label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                    <input type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none" placeholder="••••••••" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Rol *</label>
                  <select value={newUser.role} onChange={(e) => setNewUser({ ...newUser, role: e.target.value })} className="w-full px-4 py-3 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-black">
                    <option value="admin">Admin</option>
                    <option value="seller">Satıcı</option>
                    <option value="customer">Müşteri</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between rounded-b-2xl">
              <button onClick={() => setShowAddModal(false)} className="px-6 py-3 border border-gray-300 rounded-full hover:bg-gray-100 font-medium">İptal</button>
              <button onClick={handleAddUser} className="bg-black text-white px-8 py-3 rounded-full hover:bg-gray-800 font-semibold flex items-center space-x-2">
                <UserPlus size={20} />
                <span>Kullanıcı Ekle</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}