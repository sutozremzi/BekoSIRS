import React, { useEffect, useState } from "react";
import { Users, Shield, ShoppingBag, User, Search, Filter, Crown, Store, UserCircle } from "lucide-react";
import api from "../services/api";

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
}

export default function AdminDashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("Tümü");

  useEffect(() => {
    api.get("/users/")
      .then((res) => {
        setUsers(Array.isArray(res.data) ? res.data : res.data.results || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const changeRole = (id: number, role: string) => {
    if (window.confirm(`Bu kullanıcının rolünü ${role} olarak değiştirmek istediğinizden emin misiniz?`)) {
      api.post(`/users/${id}/change_role/`, { role })
        .then(() => window.location.reload());
    }
  };

  const filteredUsers = users.filter((user) => {
    const matchesSearch =
      user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = roleFilter === "Tümü" || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "admin":
        return <Crown size={18} className="text-yellow-500" />;
      case "seller":
        return <Store size={18} className="text-green-500" />;
      case "customer":
        return <UserCircle size={18} className="text-blue-500" />;
      default:
        return <User size={18} className="text-gray-500" />;
    }
  };

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
      case "admin":
        return "Admin";
      case "seller":
        return "Satıcı";
      case "customer":
        return "Müşteri";
      default:
        return role;
    }
  };

  const roleStats = {
    total: users.length,
    admin: users.filter((u) => u.role === "admin").length,
    seller: users.filter((u) => u.role === "seller").length,
    customer: users.filter((u) => u.role === "customer").length,
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center space-x-3">
            <Users size={28} className="text-blue-500" />
            <h1 className="text-2xl font-bold text-gray-900">Kullanıcı Yönetimi</h1>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
        <div className="max-w-7xl mx-auto px-6 py-12">
          <p className="text-gray-400 text-sm font-medium mb-2">KULLANICI YÖNETİMİ</p>
          <h2 className="text-3xl font-bold mb-2">Kullanıcıları Yönetin</h2>
          <p className="text-gray-300">Kullanıcı rollerini düzenleyin ve yönetin</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <Users size={24} className="text-gray-600" />
              <span className="text-3xl font-bold text-gray-900">{roleStats.total}</span>
            </div>
            <p className="text-gray-600 font-medium">Toplam Kullanıcı</p>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <Crown size={24} className="text-yellow-500" />
              <span className="text-3xl font-bold text-yellow-600">{roleStats.admin}</span>
            </div>
            <p className="text-gray-600 font-medium">Admin</p>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <Store size={24} className="text-green-500" />
              <span className="text-3xl font-bold text-green-600">{roleStats.seller}</span>
            </div>
            <p className="text-gray-600 font-medium">Satıcı</p>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <UserCircle size={24} className="text-blue-500" />
              <span className="text-3xl font-bold text-blue-600">{roleStats.customer}</span>
            </div>
            <p className="text-gray-600 font-medium">Müşteri</p>
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

        {/* Loading State */}
        {loading ? (
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-black mx-auto"></div>
            <p className="text-gray-600 mt-4 text-lg">Kullanıcılar yükleniyor...</p>
          </div>
        ) : (
          /* Users Table */
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Kullanıcı Adı
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      E-posta
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Rol
                    </th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      İşlemler
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredUsers.length > 0 ? (
                    filteredUsers.map((user) => (
                      <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                          #{user.id}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
                              <User size={20} className="text-gray-600" />
                            </div>
                            <span className="font-medium text-gray-900">{user.username}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">{user.email}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-2">
                            {getRoleIcon(user.role)}
                            <span
                              className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRoleBadgeColor(
                                user.role
                              )}`}
                            >
                              {getRoleDisplayName(user.role)}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-center space-x-2">
                            <button
                              onClick={() => changeRole(user.id, "admin")}
                              className="px-3 py-1.5 bg-yellow-50 text-yellow-700 rounded-lg hover:bg-yellow-100 transition-colors text-sm font-medium border border-yellow-200"
                              title="Admin Yap"
                            >
                              <Crown size={16} className="inline mr-1" />
                              Admin
                            </button>
                            <button
                              onClick={() => changeRole(user.id, "seller")}
                              className="px-3 py-1.5 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors text-sm font-medium border border-green-200"
                              title="Satıcı Yap"
                            >
                              <Store size={16} className="inline mr-1" />
                              Satıcı
                            </button>
                            <button
                              onClick={() => changeRole(user.id, "customer")}
                              className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors text-sm font-medium border border-blue-200"
                              title="Müşteri Yap"
                            >
                              <UserCircle size={16} className="inline mr-1" />
                              Müşteri
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-6 py-16 text-center">
                        <Users size={48} className="mx-auto text-gray-300 mb-3" />
                        <p className="text-gray-600 font-medium">Kullanıcı bulunamadı</p>
                        <p className="text-gray-500 text-sm mt-1">
                          Arama kriterlerinizi değiştirmeyi deneyin
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}