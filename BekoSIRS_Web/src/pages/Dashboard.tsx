import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import { Package, AlertTriangle, Activity, TrendingUp, ShoppingCart, Clock, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { KpiCard, AlertItem, SimpleBarChart } from "./DashboardComponents";

interface DashboardData {
  kpis: {
    total_products: number;
    out_of_stock: number;
    low_stock: number;
    pending_requests: number;
  };
  recent_products: any[];
  chart_data: { name: string; value: number }[];
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem("access");
        if (!token) throw new Error("Giriş yapmanız gerekiyor");

        const res = await fetch("http://127.0.0.1:8000/api/dashboard/summary/", {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) throw new Error("Veri yüklenemedi");

        const jsonData = await res.json();
        setData(jsonData);
      } catch (err: any) {
        console.error("Dashboard fetch error:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex bg-gray-50 min-h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin text-blue-600">
            <Package size={40} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex bg-gray-50 min-h-screen">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
          <div className="px-8 py-5 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-sm text-gray-500 mt-1">Sistemin genel durumunu buradan takip edebilirsiniz.</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                Sistem Aktif
              </span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-[1920px] mx-auto space-y-8">

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <KpiCard
                title="Toplam Ürün"
                value={data?.kpis.total_products || 0}
                icon={Package}
                color="blue"
                onClick={() => navigate("/dashboard/products")}
                subtext="Envanterdeki tüm ürünler"
              />
              <KpiCard
                title="Stok Tükendi"
                value={data?.kpis.out_of_stock || 0}
                icon={AlertTriangle}
                color="red"
                onClick={() => navigate("/dashboard/products?stock=out_of_stock")}
                subtext="Acil stok girişi gerekli"
              />
              <KpiCard
                title="Düşük Stok"
                value={data?.kpis.low_stock || 0}
                icon={TrendingUp}
                color="yellow"
                onClick={() => navigate("/dashboard/products?stock=low_stock")}
                subtext="10 adetin altındaki ürünler"
              />
              <KpiCard
                title="Bekleyen Talepler"
                value={data?.kpis.pending_requests || 0}
                icon={Clock}
                color="purple"
                onClick={() => navigate("/dashboard/service-requests")}
                subtext="İşlem bekleyen servis talepleri"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left Column: Recent Activity */}
              <div className="lg:col-span-2 space-y-8">
                <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
                  <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center">
                    <h3 className="font-bold text-gray-900">Son Eklenen Ürünler</h3>
                    <button
                      onClick={() => navigate("/dashboard/products")}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Tümünü Gör
                    </button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="bg-gray-50 text-gray-500 font-medium">
                        <tr>
                          <th className="px-6 py-3">Ürün</th>
                          <th className="px-6 py-3">Kategori</th>
                          <th className="px-6 py-3">Fiyat</th>
                          <th className="px-6 py-3">Stok</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {data?.recent_products.map((p: any) => (
                          <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                            <td className="px-6 py-4 font-medium text-gray-900">{p.name}</td>
                            <td className="px-6 py-4 text-gray-500">{p.category?.name || '-'}</td>
                            <td className="px-6 py-4 text-gray-900 font-semibold">{parseFloat(p.price).toLocaleString('tr-TR')} ₺</td>
                            <td className="px-6 py-4">
                              <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${p.stock === 0 ? 'bg-red-100 text-red-700' :
                                p.stock < 10 ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-green-100 text-green-700'
                                }`}>
                                {p.stock} adet
                              </span>
                            </td>
                          </tr>
                        )) || (
                            <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">Henüz veri yok</td></tr>
                          )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Analytics Chart */}
                <div className="h-80">
                  <SimpleBarChart
                    title="Stok Durumu Özeti"
                    data={data?.chart_data || []}
                  />
                </div>
              </div>

              {/* Right Column: Alerts Panel */}
              <div className="space-y-6">
                <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-6">
                  <div className="flex items-center gap-2 mb-6">
                    <Activity className="text-blue-600" size={20} />
                    <h3 className="font-bold text-gray-900">Sistem Uyarıları</h3>
                  </div>

                  <div className="space-y-3">
                    {data?.kpis.out_of_stock ? (
                      <AlertItem
                        severity="critical"
                        title="Stok Tükendi"
                        message={`${data.kpis.out_of_stock} ürünün stoğu bitti. Acil sipariş verilmeli.`}
                        onClick={() => navigate("/dashboard/products?stock=out_of_stock")}
                      />
                    ) : null}

                    {data?.kpis.low_stock ? (
                      <AlertItem
                        severity="warning"
                        title="Stok Azalıyor"
                        message={`${data.kpis.low_stock} ürün kritik seviyenin altında.`}
                        onClick={() => navigate("/dashboard/products?stock=low_stock")}
                      />
                    ) : null}

                    {data?.kpis.pending_requests ? (
                      <AlertItem
                        severity="info"
                        title="Bekleyen İşler"
                        message={`${data.kpis.pending_requests} adet servis talebi işlem bekliyor.`}
                        onClick={() => navigate("/dashboard/service-requests")}
                      />
                    ) : null}

                    {!data?.kpis.out_of_stock && !data?.kpis.low_stock && !data?.kpis.pending_requests && (
                      <div className="text-center py-8">
                        <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-3">
                          <Package />
                        </div>
                        <p className="text-gray-900 font-medium">Her şey yolunda!</p>
                        <p className="text-sm text-gray-500">Şu an acil bir durum yok.</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Quick Actions Support Panel */}
                <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl shadow-sm p-6 text-white">
                  <h3 className="font-bold text-lg mb-2">Hızlı İşlemler</h3>
                  <p className="text-gray-400 text-sm mb-6">Sık kullanılan işlemler</p>

                  <div className="space-y-3">
                    <button
                      onClick={() => navigate("/dashboard/products/add")}
                      className="w-full bg-white/10 hover:bg-white/20 transition-colors p-3 rounded-xl flex items-center gap-3 text-sm font-medium"
                    >
                      <div className="p-2 bg-white/10 rounded-lg"><Plus size={16} /></div>
                      Yeni Ürün Ekle
                    </button>
                    <button
                      onClick={() => navigate("/dashboard/products")}
                      className="w-full bg-white/10 hover:bg-white/20 transition-colors p-3 rounded-xl flex items-center gap-3 text-sm font-medium"
                    >
                      <div className="p-2 bg-white/10 rounded-lg"><ShoppingCart size={16} /></div>
                      Ürünleri Yönet
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}