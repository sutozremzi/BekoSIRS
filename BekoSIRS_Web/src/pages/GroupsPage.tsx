import React, { useEffect, useState } from "react";
import { Layers, Plus, Shield, Lock, ChevronRight, Check, X } from "lucide-react";
import Sidebar from "../components/Sidebar";
import api from "../services/api";

export default function GroupsPage() {
  const [groups, setGroups] = useState<any[]>([]);
  const [permissions, setPermissions] = useState<any[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<number | null>(null);
  const [groupPerms, setGroupPerms] = useState<any[]>([]);
  const [newGroupName, setNewGroupName] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem("access");

  useEffect(() => {
    const fetchGroups = async () => {
      try {
        const res = await api.get("/groups/");
        setGroups(Array.isArray(res.data) ? res.data : res.data.results || []);
      } catch (error) {
        console.error("Error fetching groups:", error);
      }
    };

    const fetchPerms = async () => {
      try {
        const res = await api.get("/groups/1/permissions/");
        setPermissions(Array.isArray(res.data) ? res.data : res.data.results || []);
      } catch (error) {
        console.error("Error fetching permissions:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchGroups();
    fetchPerms();
  }, []);

  const handleSelectGroup = async (id: number) => {
    setSelectedGroup(id);
    try {
      const res = await api.get(`/groups/${id}/permissions/`);
      setGroupPerms(res.data);
    } catch (error) {
      console.error("Error fetching group permissions:", error);
    }
  };

  const handleAddPermission = async (permId: number) => {
    if (!selectedGroup) return;
    try {
      await api.post(`/groups/${selectedGroup}/add_permission/`, { permission_id: permId });
      handleSelectGroup(selectedGroup);
    } catch (error) {
      console.error("Error adding permission:", error);
    }
  };

  const handleAddGroup = async () => {
    if (!newGroupName) return;
    try {
      await api.post("/groups/", { name: newGroupName });
      setNewGroupName("");
      setShowAddModal(false);
      window.location.reload();
    } catch (error) {
      console.error("Error adding group:", error);
    }
  };

  const isPermissionInGroup = (permId: number) => {
    return groupPerms.some((p) => p.id === permId);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-black mx-auto"></div>
            <p className="text-gray-600 mt-4 text-lg">Yükleniyor...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sol Menü */}
      <Sidebar />

      {/* Sağ İçerik Alanı */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Layers size={28} className="text-blue-500" />
                <h1 className="text-2xl font-bold text-gray-900">Grup & İzin Yönetimi</h1>
              </div>
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-black text-white px-6 py-2.5 rounded-full hover:bg-gray-800 transition-all font-medium flex items-center space-x-2"
              >
                <Plus size={20} />
                <span>Yeni Grup</span>
              </button>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
          <div className="max-w-7xl mx-auto px-6 py-12">
            <p className="text-gray-400 text-sm font-medium mb-2">YÖNETİM PANELİ</p>
            <h2 className="text-3xl font-bold mb-2">Grup ve İzinleri Yönetin</h2>
            <p className="text-gray-300">Kullanıcı gruplarını oluşturun ve izinlerini düzenleyin</p>
          </div>
        </div>

        {/* Main Content Area */}
        <main className="max-w-7xl mx-auto w-full px-6 py-8">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <Layers size={24} className="text-blue-500" />
                <span className="text-3xl font-bold text-gray-900">{groups.length}</span>
              </div>
              <p className="text-gray-600 font-medium">Toplam Grup</p>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <Shield size={24} className="text-green-500" />
                <span className="text-3xl font-bold text-gray-900">{permissions.length}</span>
              </div>
              <p className="text-gray-600 font-medium">Toplam İzin</p>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <Lock size={24} className="text-purple-500" />
                <span className="text-3xl font-bold text-gray-900">{groupPerms.length}</span>
              </div>
              <p className="text-gray-600 font-medium">Seçili Grup İzinleri</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Groups List */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="bg-gray-50 border-b border-gray-200 px-6 py-4">
                <h2 className="font-bold text-lg flex items-center space-x-2">
                  <Layers size={20} />
                  <span>Gruplar</span>
                </h2>
              </div>
              <div className="p-4 space-y-2 max-h-[600px] overflow-y-auto">
                {groups.length > 0 ? (
                  groups.map((g) => (
                    <button
                      key={g.id}
                      onClick={() => handleSelectGroup(g.id)}
                      className={`w-full flex items-center justify-between p-4 rounded-xl transition-all duration-200 ${selectedGroup === g.id
                        ? "bg-black text-white shadow-lg"
                        : "bg-gray-50 text-gray-700 hover:bg-gray-100"
                        }`}
                    >
                      <div className="flex items-center space-x-3">
                        <div
                          className={`w-10 h-10 rounded-full flex items-center justify-center ${selectedGroup === g.id ? "bg-white bg-opacity-20" : "bg-gray-200"
                            }`}
                        >
                          <Layers
                            size={18}
                            className={selectedGroup === g.id ? "text-white" : "text-gray-600"}
                          />
                        </div>
                        <span className="font-semibold">{g.name}</span>
                      </div>
                      <ChevronRight
                        size={20}
                        className={selectedGroup === g.id ? "text-white" : "text-gray-400"}
                      />
                    </button>
                  ))
                ) : (
                  <div className="text-center py-12">
                    <Layers size={48} className="mx-auto text-gray-300 mb-3" />
                    <p className="text-gray-600 font-medium">Henüz grup yok</p>
                  </div>
                )}
              </div>
            </div>

            {/* Permissions Management */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="bg-gray-50 border-b border-gray-200 px-6 py-4">
                <h2 className="font-bold text-lg flex items-center space-x-2">
                  <Shield size={20} />
                  <span>İzin Yönetimi</span>
                </h2>
              </div>
              <div className="p-6">
                {selectedGroup ? (
                  <>
                    <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                      <p className="text-sm text-blue-600 font-medium mb-1">Seçili Grup</p>
                      <p className="text-lg font-bold text-blue-900">
                        {groups.find((g) => g.id === selectedGroup)?.name}
                      </p>
                    </div>

                    <div className="space-y-4">
                      <h3 className="font-semibold text-gray-900 flex items-center space-x-2">
                        <Shield size={18} />
                        <span>İzinler</span>
                      </h3>

                      <div className="max-h-[400px] overflow-y-auto space-y-2">
                        {permissions.map((p) => {
                          const hasPermission = isPermissionInGroup(p.id);
                          return (
                            <div
                              key={p.id}
                              className={`flex items-center justify-between p-4 rounded-xl border-2 transition-all ${hasPermission
                                ? "border-green-500 bg-green-50"
                                : "border-gray-200 bg-white hover:border-gray-300"
                                }`}
                            >
                              <div className="flex items-center space-x-3">
                                {hasPermission ? (
                                  <Check size={20} className="text-green-600" />
                                ) : (
                                  <Lock size={20} className="text-gray-400" />
                                )}
                                <span
                                  className={`font-medium ${hasPermission ? "text-green-900" : "text-gray-700"
                                    }`}
                                >
                                  {p.name}
                                </span>
                              </div>
                              {!hasPermission && (
                                <button
                                  onClick={() => handleAddPermission(p.id)}
                                  className="bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-all text-sm font-medium flex items-center space-x-1"
                                >
                                  <Plus size={16} />
                                  <span>Ekle</span>
                                </button>
                              )}
                              {hasPermission && (
                                <span className="text-green-600 text-sm font-semibold">Aktif</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-16">
                    <Shield size={64} className="mx-auto text-gray-300 mb-4" />
                    <p className="text-gray-600 font-medium mb-2">
                      İzinleri yönetmek için bir grup seçin
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Add Group Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-md w-full">
            <div className="border-b border-gray-200 px-6 py-4">
              <h2 className="text-2xl font-bold flex items-center space-x-2">
                <Plus size={24} />
                <span>Yeni Grup Ekle</span>
              </h2>
            </div>
            <div className="p-6">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Grup Adı *</label>
              <input
                type="text"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="Örn: Yöneticiler"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-black"
              />
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between rounded-b-2xl">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setNewGroupName("");
                }}
                className="px-6 py-3 border border-gray-300 rounded-full hover:bg-gray-100 transition-all font-medium text-gray-700"
              >
                İptal
              </button>
              <button
                onClick={handleAddGroup}
                disabled={!newGroupName}
                className="bg-black text-white px-8 py-3 rounded-full hover:bg-gray-800 transition-all font-semibold flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus size={20} />
                <span>Grup Ekle</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}