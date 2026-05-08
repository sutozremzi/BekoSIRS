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
  Truck,
  Trash2,
} from "lucide-react";
import Sidebar from "../components/Sidebar";
import ConfirmDialog from "../components/ConfirmDialog";
import api from "../services/api";
import { useTranslation } from "react-i18next";

export default function UsersPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newUser, setNewUser] = useState({
    username: "",
    email: "",
    password: "",
    role: "customer",
  });
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [userToDelete, setUserToDelete] = useState<any>(null);

  const token = localStorage.getItem("access");

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const res = await api.get("/users/", { params: { page_size: 1000 } });
        setUsers(Array.isArray(res.data) ? res.data : res.data.results || []);
      } catch (err: any) {
        setError(err.message || t('users.errFetch'));
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const handleRoleChange = async (id: number, newRole: string) => {
    if (window.confirm(t('users.confirmRoleChange', { role: getRoleDisplayName(newRole) }))) {
      try {
        await api.post(`/users/${id}/set_role/`, { role: newRole });
        setUsers((prev) =>
          prev.map((u) => (u.id === id ? { ...u, role: newRole } : u))
        );
      } catch (err: any) {
        setError(err.message || t('users.errRoleUpdate'));
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
      alert(t('users.successAdd'));
    } catch (err: any) {
      setError(err.message || t('users.errAdd'));
    }
  };

  const handleDeleteClick = (user: any) => {
    setUserToDelete(user);
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    if (!userToDelete) return;
    try {
      await api.delete(`/users/${userToDelete.id}/`);
      setUsers((prev) => prev.filter((u) => u.id !== userToDelete.id));
      setShowDeleteModal(false);
      setUserToDelete(null);
    } catch (err: any) {
      alert(t('users.errDelete'));
      console.error(err);
    }
  };

  const filteredUsers = users.filter((user) => {
    const fullName = `${user.first_name || ""} ${user.last_name || ""}`.trim();
    const matchesSearch =
      (user.username || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (user.email || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      fullName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = roleFilter === "all" || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });
  const pageSize = 20;
  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const pagedUsers = filteredUsers.slice((safeCurrentPage - 1) * pageSize, safeCurrentPage * pageSize);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, roleFilter]);

  const roleCardClass = (targetRole: string) =>
    `bg-white rounded-2xl shadow-sm border p-6 text-left transition-all ${
      roleFilter === targetRole
        ? "border-black ring-2 ring-black/10"
        : "border-gray-200 hover:border-gray-400"
    }`;

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "admin":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      case "seller":
        return "bg-green-100 text-green-800 border-green-300";
      case "customer":
        return "bg-blue-100 text-blue-800 border-blue-300";
      case "delivery":
        return "bg-orange-100 text-orange-800 border-orange-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const getRoleDisplayName = (role: string) => {
    switch (role) {
      case "admin": return t('users.roleAdmin');
      case "seller": return t('users.roleSeller');
      case "customer": return t('users.roleCustomer');
      case "delivery": return t('users.roleDelivery');
      default: return role;
    }
  };

  const roleStats = {
    total: users.length,
    admin: users.filter((u) => u.role === "admin").length,
    seller: users.filter((u) => u.role === "seller").length,
    customer: users.filter((u) => u.role === "customer").length,
    delivery: users.filter((u) => u.role === "delivery").length,
    active: users.filter((u) => u.is_active).length,
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-black mx-auto"></div>
            <p className="text-gray-600 mt-4 text-lg">{t('users.loading')}</p>
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
                <h1 className="text-2xl font-bold text-gray-900">{t('users.title')}</h1>
              </div>
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-black text-white px-6 py-2.5 rounded-full hover:bg-gray-800 transition-all font-medium flex items-center space-x-2"
              >
                <UserPlus size={20} />
                <span>{t('users.btnAdd')}</span>
              </button>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
          <div className="max-w-7xl mx-auto px-6 py-12">
            <p className="text-gray-400 text-sm font-medium mb-2">{t('users.heroTag')}</p>
            <h2 className="text-3xl font-bold mb-2">{t('users.heroTitle')}</h2>
            <p className="text-gray-300">{t('users.heroDesc')}</p>
          </div>
        </div>

        <main className="max-w-7xl mx-auto w-full px-6 py-8 overflow-y-auto">
          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-8">
            <button type="button" onClick={() => setRoleFilter("all")} className={roleCardClass("all")}>
              <div className="flex items-center justify-between mb-2">
                <Users size={24} className="text-gray-600" />
                <span className="text-2xl font-bold text-gray-900">{roleStats.total}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">{t('users.statTotal')}</p>
            </button>
            <button type="button" onClick={() => setRoleFilter("admin")} className={roleCardClass("admin")}>
              <div className="flex items-center justify-between mb-2">
                <Crown size={24} className="text-yellow-500" />
                <span className="text-2xl font-bold text-yellow-600">{roleStats.admin}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">{t('users.roleAdmin')}</p>
            </button>
            <button type="button" onClick={() => setRoleFilter("seller")} className={roleCardClass("seller")}>
              <div className="flex items-center justify-between mb-2">
                <Store size={24} className="text-green-500" />
                <span className="text-2xl font-bold text-green-600">{roleStats.seller}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">{t('users.roleSeller')}</p>
            </button>
            <button type="button" onClick={() => setRoleFilter("customer")} className={roleCardClass("customer")}>
              <div className="flex items-center justify-between mb-2">
                <UserCircle size={24} className="text-blue-500" />
                <span className="text-2xl font-bold text-blue-600">{roleStats.customer}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">{t('users.roleCustomer')}</p>
            </button>
            <button type="button" onClick={() => setRoleFilter("delivery")} className={roleCardClass("delivery")}>
              <div className="flex items-center justify-between mb-2">
                <Truck size={24} className="text-orange-500" />
                <span className="text-2xl font-bold text-orange-600">{roleStats.delivery}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">{t('users.roleDelivery')}</p>
            </button>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <CheckCircle size={24} className="text-emerald-500" />
                <span className="text-2xl font-bold text-emerald-600">{roleStats.active}</span>
              </div>
              <p className="text-gray-600 text-sm font-medium">{t('users.statActive')}</p>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-8">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder={t('users.searchPlaceholder')}
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
                  <option value="all">{t('users.filterAllRoles')}</option>
                  <option value="admin">{t('users.roleAdmin')}</option>
                  <option value="seller">{t('users.roleSeller')}</option>
                  <option value="customer">{t('users.roleCustomer')}</option>
                  <option value="delivery">{t('users.roleDelivery')}</option>
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
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('users.colId')}</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('users.colUser')}</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('users.colEmail')}</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('users.colRole')}</th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('users.colStatus')}</th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('users.colActions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {pagedUsers.length > 0 ? (
                    pagedUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">#{u.id}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                              <span className="text-white font-bold text-sm">
                                {u.username.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <div className="font-medium text-gray-900">
                                {`${u.first_name || ""} ${u.last_name || ""}`.trim() || u.username}
                              </div>
                              <div className="text-xs text-gray-500">{u.username}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">{u.email}</td>
                        <td className="px-6 py-4">
                          <select
                            value={u.role}
                            onChange={(e) => handleRoleChange(u.id, e.target.value)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-semibold border cursor-pointer transition-all ${getRoleBadgeColor(u.role)}`}
                          >
                            <option value="admin">⚙️ {t('users.roleAdmin')}</option>
                            <option value="seller">🏪 {t('users.roleSeller')}</option>
                            <option value="customer">👤 {t('users.roleCustomer')}</option>
                            <option value="delivery">🚚 {t('users.roleDelivery')}</option>
                          </select>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <div className="flex items-center justify-center space-x-2">
                            {u.is_active ? (
                              <><CheckCircle size={18} className="text-green-600" /><span className="text-sm font-semibold text-green-700">{t('users.statusActive')}</span></>
                            ) : (
                              <><XCircle size={18} className="text-red-600" /><span className="text-sm font-semibold text-red-700">{t('users.statusPassive')}</span></>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={() => handleDeleteClick(u)}
                            className="p-2 hover:bg-red-50 rounded-lg transition-colors group"
                            title="Sil"
                          >
                            <Trash2 size={18} className="text-gray-600 group-hover:text-red-600" />
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-6 py-16 text-center">
                        <Users size={48} className="mx-auto text-gray-300 mb-3" />
                        <p className="text-gray-600 font-medium">{t('users.noUsers')}</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {filteredUsers.length > 0 && (
            <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <p className="text-sm text-gray-600">
                {filteredUsers.length} kullanicidan {(safeCurrentPage - 1) * pageSize + 1}-{Math.min(safeCurrentPage * pageSize, filteredUsers.length)} arasi gosteriliyor
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                  disabled={safeCurrentPage === 1}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Onceki
                </button>
                {Array.from({ length: totalPages }, (_, index) => index + 1)
                  .filter((page) => page === 1 || page === totalPages || Math.abs(page - safeCurrentPage) <= 2)
                  .map((page, index, pages) => (
                    <React.Fragment key={page}>
                      {index > 0 && page - pages[index - 1] > 1 && (
                        <span className="px-2 text-gray-400">...</span>
                      )}
                      <button
                        type="button"
                        onClick={() => setCurrentPage(page)}
                        className={`min-w-10 px-3 py-2 rounded-lg text-sm font-semibold border ${
                          safeCurrentPage === page
                            ? "bg-black text-white border-black"
                            : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                        }`}
                      >
                        {page}
                      </button>
                    </React.Fragment>
                  ))}
                <button
                  type="button"
                  onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                  disabled={safeCurrentPage === totalPages}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Sonraki
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full">
            <div className="border-b border-gray-200 px-6 py-4">
              <h2 className="text-2xl font-bold flex items-center space-x-2">
                <UserPlus size={24} />
                <span>{t('users.modalAddTitle')}</span>
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">{t('users.lblUsername')}</label>
                  <div className="relative">
                    <User className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                    <input type="text" value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none" placeholder="kullaniciadi" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">{t('users.lblEmail')}</label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                    <input type="email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none" placeholder="ornek@email.com" />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">{t('users.lblPassword')}</label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                    <input type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black outline-none" placeholder="••••••••" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">{t('users.lblRole')}</label>
                  <select value={newUser.role} onChange={(e) => setNewUser({ ...newUser, role: e.target.value })} className="w-full px-4 py-3 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-black">
                    <option value="admin">{t('users.roleAdmin')}</option>
                    <option value="seller">{t('users.roleSeller')}</option>
                    <option value="customer">{t('users.roleCustomer')}</option>
                    <option value="delivery">{t('users.roleDelivery')}</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between rounded-b-2xl">
              <button onClick={() => setShowAddModal(false)} className="px-6 py-3 border border-gray-300 rounded-full hover:bg-gray-100 font-medium">{t('users.btnCancel')}</button>
              <button onClick={handleAddUser} className="bg-black text-white px-8 py-3 rounded-full hover:bg-gray-800 font-semibold flex items-center space-x-2">
                <UserPlus size={20} />
                <span>{t('users.btnAddSubmit')}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmDialog
        open={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setUserToDelete(null);
        }}
        onConfirm={handleConfirmDelete}
        title={t('users.modalDeleteTitle')}
        message={t('users.modalDeleteDesc', { user: userToDelete?.username })}
        confirmText={t('users.btnYesDelete')}
        cancelText={t('users.btnCancel')}
        variant="danger"
      />
    </div>
  );
}
