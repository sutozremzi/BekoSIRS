import React, { useEffect, useState, useMemo } from "react";
import { Layers, Plus, Shield, Lock, ChevronRight, Check, X, Save, Search, Users, CheckSquare, Square } from "lucide-react";
import Sidebar from "../components/Sidebar";
import api from "../services/api";
import { ToastContainer, type ToastType } from "../components/Toast";
import { useTranslation } from "react-i18next";

export default function GroupsPage() {
  const { t } = useTranslation();
  const [roles, setRoles] = useState<any[]>([]);
  const [allPermissions, setAllPermissions] = useState<any[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [rolePermissionIds, setRolePermissionIds] = useState<number[]>([]);
  const [initialRolePermissionIds, setInitialRolePermissionIds] = useState<number[]>([]);

  const [newRoleName, setNewRoleName] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [permSearchTerm, setPermSearchTerm] = useState("");
  const [toasts, setToasts] = useState<{ id: string; type: ToastType; message: string }[]>([]);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [rolesRes, permsRes] = await Promise.all([
          api.get("/groups/"),
          api.get("/groups/available_permissions/")
        ]);

        const rawRoles = Array.isArray(rolesRes.data) ? rolesRes.data : rolesRes.data.results || [];
        setRoles(rawRoles.filter((r: any) => !['müşteri', 'customer'].includes(r.name.toLowerCase())));
        setAllPermissions(permsRes.data);
      } catch (error) {
        console.error("Veri yükleme hatası:", error);
        showToast("error", t('groups.errFetchRoles'));
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const showToast = (type: ToastType, message: string) => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, type, message }]);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  const selectedRoleName = useMemo(() =>
    roles.find(r => r.id === selectedRoleId)?.name
    , [roles, selectedRoleId]);

  const isAdmin = selectedRoleName?.toLowerCase() === 'admin';

  const handleSelectRole = async (id: number) => {
    setSelectedRoleId(id);
    try {
      const res = await api.get(`/groups/${id}/permissions/`);
      const ids = res.data;
      setRolePermissionIds(ids);
      setInitialRolePermissionIds(ids);
    } catch (error) {
      console.error("Rol yetkileri alınamadı:", error);
      showToast("error", t('groups.errFetchPerms'));
    }
  };

  const handleAddRole = async () => {
    if (!newRoleName.trim()) return;
    try {
      const res = await api.post("/groups/", { name: newRoleName });
      setRoles([...roles, res.data]);
      setNewRoleName("");
      setShowAddModal(false);
      showToast("success", t('groups.successAddRole'));
    } catch (error) {
      console.error("Rol ekleme hatası:", error);
      showToast("error", t('groups.errAddRole'));
    }
  };

  const handleTogglePermission = (permId: number) => {
    if (isAdmin) return;
    setRolePermissionIds(prev => {
      if (prev.includes(permId)) {
        return prev.filter(id => id !== permId);
      } else {
        return [...prev, permId];
      }
    });
  };

  const handleSavePermissions = async () => {
    if (!selectedRoleId || isAdmin) return;
    setSaving(true);
    try {
      await api.post(`/groups/${selectedRoleId}/update_permissions/`, {
        permission_ids: rolePermissionIds
      });
      setInitialRolePermissionIds(rolePermissionIds);
      showToast("success", t('groups.successSavePerms'));
    } catch (error) {
      console.error("Yetki güncelleme hatası:", error);
      showToast("error", t('groups.errSavePerms'));
    } finally {
      setSaving(false);
    }
  };

  // Has changes?
  const hasChanges = useMemo(() => {
    if (isAdmin) return false;
    if (rolePermissionIds.length !== initialRolePermissionIds.length) return true;
    const sorted1 = [...rolePermissionIds].sort();
    const sorted2 = [...initialRolePermissionIds].sort();
    return JSON.stringify(sorted1) !== JSON.stringify(sorted2);
  }, [rolePermissionIds, initialRolePermissionIds, isAdmin]);

  const filteredPermissions = useMemo(() => {
    return allPermissions.filter(p =>
      p.name.toLowerCase().includes(permSearchTerm.toLowerCase()) ||
      p.codename.toLowerCase().includes(permSearchTerm.toLowerCase())
    );
  }, [allPermissions, permSearchTerm]);

  // Bulk Selection Logic
  const areAllFilteredSelected = useMemo(() => {
    if (filteredPermissions.length === 0) return false;
    return filteredPermissions.every(p => rolePermissionIds.includes(p.id));
  }, [filteredPermissions, rolePermissionIds]);

  const handleToggleAll = () => {
    if (isAdmin) return;

    if (areAllFilteredSelected) {
      // Deselect all filtered
      const filteredIds = filteredPermissions.map(p => p.id);
      setRolePermissionIds(prev => prev.filter(id => !filteredIds.includes(id)));
    } else {
      // Select all filtered
      const filteredIds = filteredPermissions.map(p => p.id);
      const newIds = new Set([...rolePermissionIds, ...filteredIds]);
      setRolePermissionIds(Array.from(newIds));
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Users size={28} className="text-blue-600" />
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">{t('groups.title')}</h1>
                  <p className="text-sm text-gray-500">{t('groups.subtitle')}</p>
                </div>
              </div>
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-black text-white px-5 py-2.5 rounded-lg hover:bg-gray-800 transition-all font-medium flex items-center space-x-2 shadow-sm"
              >
                <Plus size={18} />
                <span>{t('groups.btnAddRole')}</span>
              </button>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto w-full px-6 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

            {/* SOL TARAF: ROLLER LİSTESİ */}
            <div className="lg:col-span-4 bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col h-[calc(100vh-12rem)]">
              <div className="bg-gray-50 border-b border-gray-200 px-5 py-4 flex justify-between items-center">
                <h2 className="font-bold text-gray-800 flex items-center gap-2">
                  <Layers size={18} />
                  <span>{t('groups.rolesTitle')}</span>
                </h2>
                <span className="text-xs font-semibold bg-gray-200 px-2 py-1 rounded-full text-gray-600">
                  {roles.length}
                </span>
              </div>

              <div className="p-3 space-y-2 overflow-y-auto flex-1">
                {roles.length > 0 ? (
                  roles.map((role) => (
                    <button
                      key={role.id}
                      onClick={() => handleSelectRole(role.id)}
                      className={`w-full flex items-center justify-between p-4 rounded-xl transition-all duration-200 text-left group ${selectedRoleId === role.id
                        ? "bg-black text-white shadow-md ring-1 ring-black"
                        : "bg-white border border-gray-100 text-gray-700 hover:bg-gray-50 hover:border-gray-200"
                        }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${selectedRoleId === role.id ? "bg-white text-black" : "bg-gray-100 text-gray-500"
                          }`}>
                          {role.name.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-semibold">{role.name}</span>
                      </div>
                      <ChevronRight
                        size={18}
                        className={`transition-transform ${selectedRoleId === role.id ? "text-white translate-x-1" : "text-gray-300 group-hover:text-gray-400"}`}
                      />
                    </button>
                  ))
                ) : (
                  <div className="text-center py-12 px-4">
                    <p className="text-gray-400">{t('groups.noRoles')}</p>
                  </div>
                )}
              </div>
            </div>

            {/* SAĞ TARAF: YETKİLER */}
            <div className="lg:col-span-8 bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col h-[calc(100vh-12rem)]">
              {selectedRoleId ? (
                <>
                  <div className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center sticky top-0 z-10 shadow-sm">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="font-bold text-lg text-gray-900">{t('groups.permsTitle', { role: selectedRoleName })}</h2>
                        {isAdmin && (
                          <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full flex items-center gap-1 font-medium">
                            <Lock size={10} /> {t('groups.fullAccess')}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500">
                        {isAdmin ? t('groups.adminDesc') : t('groups.selectDesc')}
                      </p>
                    </div>

                    {!isAdmin && (
                      <button
                        onClick={handleSavePermissions}
                        disabled={!hasChanges || saving}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all ${hasChanges
                          ? "bg-blue-600 text-white hover:bg-blue-700 shadow-md"
                          : "bg-gray-100 text-gray-400 cursor-not-allowed"
                          }`}
                      >
                        {saving ? (
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                          <Save size={18} />
                        )}
                        <span>{t('groups.btnSave')}</span>
                      </button>
                    )}
                  </div>

                  {/* Search and Bulk Actions */}
                  <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex gap-4">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                      <input
                        type="text"
                        placeholder={t('groups.searchPerms')}
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        value={permSearchTerm}
                        onChange={e => setPermSearchTerm(e.target.value)}
                      />
                    </div>

                    {!isAdmin && (
                      <button
                        onClick={handleToggleAll}
                        className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                      >
                        {areAllFilteredSelected ? (
                          <>
                            <Square size={16} />
                            {t('groups.deselectAll')}
                          </>
                        ) : (
                          <>
                            <CheckSquare size={16} />
                            {t('groups.selectAll')}
                          </>
                        )}
                      </button>
                    )}
                  </div>

                  <div className="flex-1 overflow-y-auto p-2">
                    {filteredPermissions.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
                        {filteredPermissions.map((perm) => {
                          // Admin is always checked
                          const isChecked = isAdmin || rolePermissionIds.includes(perm.id);
                          return (
                            <label
                              key={perm.id}
                              className={`flex items-start gap-3 p-3 rounded-lg border transition-all select-none ${isAdmin
                                ? "bg-gray-50 border-gray-100 cursor-not-allowed opacity-80"
                                : "cursor-pointer"
                                } ${isChecked && !isAdmin
                                  ? "bg-blue-50 border-blue-200 shadow-sm"
                                  : "bg-white border-gray-100 hover:border-gray-200 hover:bg-gray-50"
                                }`}
                            >
                              <div className="pt-0.5">
                                <input
                                  type="checkbox"
                                  className={`w-4 h-4 rounded border-gray-300 ${isAdmin ? "text-gray-400 focus:ring-0" : "text-blue-600 focus:ring-blue-500"}`}
                                  checked={isChecked}
                                  disabled={isAdmin}
                                  onChange={() => handleTogglePermission(perm.id)}
                                />
                              </div>
                              <div className="flex-1">
                                <div className={`text-sm font-medium ${isChecked && !isAdmin ? "text-blue-900" : "text-gray-700"}`}>
                                  {perm.name}
                                </div>
                                <div className="text-xs text-gray-500 mt-0.5 font-mono bg-black/5 inline-block px-1.5 py-0.5 rounded">
                                  {perm.codename}
                                </div>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-center py-12 text-gray-400">
                        {t('groups.noPermsFound')}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8 text-center">
                  <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-6">
                    <Shield size={40} className="text-gray-300" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">{t('groups.selectRoleTitle')}</h3>
                  <p className="max-w-md">{t('groups.selectRoleDesc')}</p>
                </div>
              )}
            </div>
          </div>
        </main>

        {/* Add Role Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl transform transition-all">
              <div className="border-b border-gray-100 px-6 py-4 flex justify-between items-center">
                <h2 className="text-xl font-bold text-gray-900">{t('groups.modalAddTitle')}</h2>
                <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">
                  <X size={24} />
                </button>
              </div>
              <div className="p-6">
                <label className="block text-sm font-semibold text-gray-700 mb-2">{t('groups.lblRoleName')}</label>
                <input
                  type="text"
                  value={newRoleName}
                  onChange={(e) => setNewRoleName(e.target.value)}
                  placeholder={t('groups.plcRoleName')}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition-all"
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-2">
                  {t('groups.descRoleAdd')}
                </p>
              </div>
              <div className="bg-gray-50 px-6 py-4 border-t border-gray-100 flex gap-3 rounded-b-2xl">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-100 font-medium text-gray-700 transition-colors"
                >
                  {t('groups.btnCancel')}
                </button>
                <button
                  onClick={handleAddRole}
                  disabled={!newRoleName.trim()}
                  className="flex-1 bg-black text-white px-4 py-2.5 rounded-lg hover:bg-gray-800 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {t('groups.btnCreate')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}