import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import { Package, AlertTriangle, Activity, TrendingUp, ShoppingCart, Clock, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { KpiCard, AlertItem, SimpleBarChart } from "./DashboardComponents";
import api from "../services/api";
import { useTranslation } from "react-i18next";

interface DashboardData {
  products: {
    total: number;
    low_stock: number;
    out_of_stock: number;
  };
  categories: { total: number };
  customers: { total: number };
  orders: { total: number };
  service_requests: {
    pending: number;
    in_progress: number;
    completed: number;
  };
  reviews: {
    pending_approval: number;
    average_rating: number;
  };
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [recentProducts, setRecentProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch dashboard summary
        const summaryRes = await api.get("/dashboard/summary/");
        setData(summaryRes.data);

        // Fetch recent products
        try {
          const productsRes = await api.get("/products/?page_size=5");
          setRecentProducts(productsRes.data.results || productsRes.data.slice?.(0, 5) || []);
        } catch (e) {
          console.warn("Could not fetch recent products:", e);
        }

      } catch (err: any) {
        console.error("Dashboard fetch error:", err);
        setError(err.message || t('dashboard.errorLoad'));
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

  if (error) {
    return (
      <div className="flex bg-gray-50 min-h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="mx-auto text-red-500 mb-4" size={48} />
            <p className="text-red-600 font-medium">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              {t('dashboard.tryAgain')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Prepare chart data from API response
  const chartData = [
    { name: t('dashboard.chartInStock'), value: (data?.products.total || 0) - (data?.products.out_of_stock || 0) - (data?.products.low_stock || 0) },
    { name: t('dashboard.chartLowStock'), value: data?.products.low_stock || 0 },
    { name: t('dashboard.chartOutOfStock'), value: data?.products.out_of_stock || 0 },
  ];

  return (
    <div className="flex bg-gray-50 min-h-screen">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
          <div className="px-8 py-5 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{t('dashboard.title')}</h1>
              <p className="text-sm text-gray-500 mt-1">{t('dashboard.subtitle')}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                {t('dashboard.systemActive')}
              </span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-[1920px] mx-auto space-y-8">

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <KpiCard
                title={t('dashboard.kpiTotalProducts')}
                value={data?.products.total || 0}
                icon={Package}
                color="blue"
                onClick={() => navigate("/dashboard/products")}
                subtext={t('dashboard.kpiTotalProductsDesc')}
              />
              <KpiCard
                title={t('dashboard.kpiOutOfStock')}
                value={data?.products.out_of_stock || 0}
                icon={AlertTriangle}
                color="red"
                onClick={() => navigate("/dashboard/products?stock=out_of_stock")}
                subtext={t('dashboard.kpiOutOfStockDesc')}
              />
              <KpiCard
                title={t('dashboard.kpiLowStock')}
                value={data?.products.low_stock || 0}
                icon={TrendingUp}
                color="yellow"
                onClick={() => navigate("/dashboard/products?stock=low_stock")}
                subtext={t('dashboard.kpiLowStockDesc')}
              />
              <KpiCard
                title={t('dashboard.kpiPendingRequests')}
                value={data?.service_requests.pending || 0}
                icon={Clock}
                color="purple"
                onClick={() => navigate("/dashboard/service-requests")}
                subtext={t('dashboard.kpiPendingRequestsDesc')}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left Column: Recent Activity */}
              <div className="lg:col-span-2 space-y-8">
                <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
                  <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center">
                    <h3 className="font-bold text-gray-900">{t('dashboard.recentProducts')}</h3>
                    <button
                      onClick={() => navigate("/dashboard/products")}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      {t('dashboard.seeAll')}
                    </button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="bg-gray-50 text-gray-500 font-medium">
                        <tr>
                          <th className="px-6 py-3">{t('dashboard.tableProduct')}</th>
                          <th className="px-6 py-3">{t('dashboard.tableCategory')}</th>
                          <th className="px-6 py-3">{t('dashboard.tablePrice')}</th>
                          <th className="px-6 py-3">{t('dashboard.tableStock')}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {recentProducts.length > 0 ? recentProducts.map((p: any) => (
                          <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                            <td className="px-6 py-4 font-medium text-gray-900">{p.name}</td>
                            <td className="px-6 py-4 text-gray-500">{p.category?.name || p.category_name || '-'}</td>
                            <td className="px-6 py-4 text-gray-900 font-semibold">{parseFloat(p.price).toLocaleString('tr-TR')} ₺</td>
                            <td className="px-6 py-4">
                              <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${p.stock === 0 ? 'bg-red-100 text-red-700' :
                                p.stock < 10 ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-green-100 text-green-700'
                                }`}>
                                {p.stock} {t('dashboard.pieces')}
                              </span>
                            </td>
                          </tr>
                        )) : (
                          <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">{t('dashboard.noData')}</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Analytics Chart */}
                <div className="h-80">
                  <SimpleBarChart
                    title={t('dashboard.chartTitle')}
                    data={chartData}
                  />
                </div>
              </div>


              {/* Right Column: Alerts Panel */}
              <div className="space-y-6">
                <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-6">
                  <div className="flex items-center gap-2 mb-6">
                    <Activity className="text-blue-600" size={20} />
                    <h3 className="font-bold text-gray-900">{t('dashboard.systemAlerts')}</h3>
                  </div>

                  <div className="space-y-3">
                    {data?.products.out_of_stock ? (
                      <AlertItem
                        severity="critical"
                        title={t('dashboard.alertOutOfStockTitle')}
                        message={t('dashboard.alertOutOfStockMsg', { count: data.products.out_of_stock })}
                        onClick={() => navigate("/dashboard/products?stock=out_of_stock")}
                      />
                    ) : null}

                    {data?.products.low_stock ? (
                      <AlertItem
                        severity="warning"
                        title={t('dashboard.alertLowStockTitle')}
                        message={t('dashboard.alertLowStockMsg', { count: data.products.low_stock })}
                        onClick={() => navigate("/dashboard/products?stock=low_stock")}
                      />
                    ) : null}

                    {data?.service_requests.pending ? (
                      <AlertItem
                        severity="info"
                        title={t('dashboard.alertPendingTitle')}
                        message={t('dashboard.alertPendingMsg', { count: data.service_requests.pending })}
                        onClick={() => navigate("/dashboard/service-requests")}
                      />
                    ) : null}

                    {!data?.products.out_of_stock && !data?.products.low_stock && !data?.service_requests.pending && (
                      <div className="text-center py-8">
                        <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-3">
                          <Package />
                        </div>
                        <p className="text-gray-900 font-medium">{t('dashboard.allGoodTitle')}</p>
                        <p className="text-sm text-gray-500">{t('dashboard.allGoodMsg')}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Quick Actions Support Panel */}
                <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl shadow-sm p-6 text-white">
                  <h3 className="font-bold text-lg mb-2">{t('dashboard.quickActions')}</h3>
                  <p className="text-gray-400 text-sm mb-6">{t('dashboard.quickActionsDesc')}</p>

                  <div className="space-y-3">
                    <button
                      onClick={() => navigate("/dashboard/products?add=true")}
                      className="w-full bg-white/10 hover:bg-white/20 transition-colors p-3 rounded-xl flex items-center gap-3 text-sm font-medium"
                    >
                      <div className="p-2 bg-white/10 rounded-lg"><Plus size={16} /></div>
                      {t('dashboard.addProduct')}
                    </button>
                    <button
                      onClick={() => navigate("/dashboard/products")}
                      className="w-full bg-white/10 hover:bg-white/20 transition-colors p-3 rounded-xl flex items-center gap-3 text-sm font-medium"
                    >
                      <div className="p-2 bg-white/10 rounded-lg"><ShoppingCart size={16} /></div>
                      {t('dashboard.manageProducts')}
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