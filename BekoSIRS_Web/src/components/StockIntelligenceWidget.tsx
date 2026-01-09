// src/components/StockIntelligenceWidget.tsx
/**
 * Stock Intelligence Dashboard Widget
 * 
 * Displays smart stock recommendations for admin dashboard:
 * - Critical alerts (products running out soon)
 * - Seasonal opportunities
 * - Top sellers and low performers
 * 
 * Usage:
 * import StockIntelligenceWidget from '@/components/StockIntelligenceWidget';
 * <StockIntelligenceWidget />
 */

import React, { useEffect, useState } from 'react';
import { stockIntelligenceAPI } from '../services/api';

// Types
interface StockAlert {
    product_id: number;
    product_name: string;
    brand: string;
    category: string;
    current_stock: number;
    sales_last_30_days: number;
    velocity: number;
    days_until_stockout: number | null;
    recommended_order_qty: number;
    urgency: 'critical' | 'warning' | 'opportunity' | 'healthy';
    message: string;
    estimated_order_cost: number;
}

interface DashboardSummary {
    summary: {
        critical_count: number;
        warning_count: number;
        opportunity_count: number;
        healthy_count: number;
        total_products: number;
    };
    critical_alerts: StockAlert[];
    opportunities: StockAlert[];
    top_sellers: Array<{ product__name: string; product__brand: string; sales_count: number }>;
    low_performers: Array<{ name: string; brand: string; stock: number }>;
}

export default function StockIntelligenceWidget() {
    const [data, setData] = useState<DashboardSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'critical' | 'opportunities' | 'sellers'>('critical');

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const response = await stockIntelligenceAPI.getDashboardSummary();
            setData(response.data);
            setError(null);
        } catch (err) {
            setError('Stok verileri yüklenemedi');
            console.error('Stock Intelligence Error:', err);
        } finally {
            setLoading(false);
        }
    };

    const getUrgencyIcon = (urgency: string) => {
        switch (urgency) {
            case 'critical': return '🔴';
            case 'warning': return '🟡';
            case 'opportunity': return '⭐';
            default: return '🟢';
        }
    };

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('tr-TR', {
            style: 'currency',
            currency: 'TRY',
            minimumFractionDigits: 0,
        }).format(value);
    };

    if (loading) {
        return (
            <div className="stock-intelligence-widget loading">
                <div className="spinner"></div>
                <span>Stok analizi yükleniyor...</span>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="stock-intelligence-widget error">
                <span>⚠️ {error || 'Veri yüklenemedi'}</span>
                <button onClick={fetchData}>Tekrar Dene</button>
            </div>
        );
    }

    return (
        <div className="stock-intelligence-widget">
            {/* Header */}
            <div className="widget-header">
                <h3>🧠 Stok Zekası</h3>
                <button className="refresh-btn" onClick={fetchData} title="Yenile">
                    🔄
                </button>
            </div>

            {/* Summary Cards */}
            <div className="summary-cards">
                <div className="card critical">
                    <span className="count">{data.summary.critical_count}</span>
                    <span className="label">🔴 Kritik</span>
                </div>
                <div className="card warning">
                    <span className="count">{data.summary.warning_count}</span>
                    <span className="label">🟡 Uyarı</span>
                </div>
                <div className="card opportunity">
                    <span className="count">{data.summary.opportunity_count}</span>
                    <span className="label">⭐ Fırsat</span>
                </div>
                <div className="card healthy">
                    <span className="count">{data.summary.healthy_count}</span>
                    <span className="label">🟢 Sağlıklı</span>
                </div>
            </div>

            {/* Tabs */}
            <div className="tabs">
                <button
                    className={activeTab === 'critical' ? 'active' : ''}
                    onClick={() => setActiveTab('critical')}
                >
                    Kritik Uyarılar ({data.critical_alerts.length})
                </button>
                <button
                    className={activeTab === 'opportunities' ? 'active' : ''}
                    onClick={() => setActiveTab('opportunities')}
                >
                    Fırsatlar ({data.opportunities.length})
                </button>
                <button
                    className={activeTab === 'sellers' ? 'active' : ''}
                    onClick={() => setActiveTab('sellers')}
                >
                    Satış Analizi
                </button>
            </div>

            {/* Content */}
            <div className="tab-content">
                {activeTab === 'critical' && (
                    <div className="alerts-list">
                        {data.critical_alerts.length === 0 ? (
                            <div className="empty-state">
                                ✅ Kritik stok uyarısı yok
                            </div>
                        ) : (
                            data.critical_alerts.map((alert) => (
                                <div key={alert.product_id} className="alert-item critical">
                                    <div className="alert-header">
                                        <span className="icon">{getUrgencyIcon(alert.urgency)}</span>
                                        <span className="name">{alert.product_name}</span>
                                        <span className="brand">{alert.brand}</span>
                                    </div>
                                    <div className="alert-details">
                                        <span className="stock">Stok: {alert.current_stock}</span>
                                        <span className="days">
                                            {alert.days_until_stockout
                                                ? `${Math.round(alert.days_until_stockout)} gün`
                                                : 'Tükendi!'}
                                        </span>
                                    </div>
                                    <div className="alert-message">{alert.message}</div>
                                    <div className="alert-action">
                                        <span className="recommendation">
                                            Önerilen sipariş: {alert.recommended_order_qty} adet
                                        </span>
                                        <span className="cost">
                                            Tahmini maliyet: {formatCurrency(alert.estimated_order_cost)}
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {activeTab === 'opportunities' && (
                    <div className="alerts-list">
                        {data.opportunities.length === 0 ? (
                            <div className="empty-state">
                                📊 Mevsimsel fırsat bulunamadı
                            </div>
                        ) : (
                            data.opportunities.map((opp) => (
                                <div key={opp.product_id} className="alert-item opportunity">
                                    <div className="alert-header">
                                        <span className="icon">⭐</span>
                                        <span className="name">{opp.product_name}</span>
                                        <span className="brand">{opp.brand}</span>
                                    </div>
                                    <div className="alert-message">{opp.message}</div>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {activeTab === 'sellers' && (
                    <div className="sales-analysis">
                        <div className="section">
                            <h4>🏆 En Çok Satanlar (Son 30 Gün)</h4>
                            <ul className="seller-list">
                                {data.top_sellers.map((seller, idx) => (
                                    <li key={idx}>
                                        <span className="rank">#{idx + 1}</span>
                                        <span className="name">{seller.product__name}</span>
                                        <span className="sales">{seller.sales_count} satış</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div className="section">
                            <h4>📉 Düşük Performans</h4>
                            <ul className="seller-list low">
                                {data.low_performers.map((low, idx) => (
                                    <li key={idx}>
                                        <span className="name">{low.name}</span>
                                        <span className="stock">{low.stock} stok, 0 satış</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}
            </div>

            <style>{`
        .stock-intelligence-widget {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .widget-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        
        .widget-header h3 {
          margin: 0;
          font-size: 18px;
          color: #111827;
        }
        
        .refresh-btn {
          background: none;
          border: none;
          font-size: 18px;
          cursor: pointer;
          padding: 4px 8px;
          border-radius: 4px;
          transition: background 0.2s;
        }
        
        .refresh-btn:hover {
          background: #f3f4f6;
        }
        
        .summary-cards {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }
        
        .summary-cards .card {
          text-align: center;
          padding: 12px;
          border-radius: 8px;
        }
        
        .card.critical { background: #fef2f2; }
        .card.warning { background: #fffbeb; }
        .card.opportunity { background: #f0fdf4; }
        .card.healthy { background: #f0f9ff; }
        
        .card .count {
          display: block;
          font-size: 24px;
          font-weight: 700;
          color: #111827;
        }
        
        .card .label {
          font-size: 12px;
          color: #6b7280;
        }
        
        .tabs {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
          border-bottom: 1px solid #e5e7eb;
          padding-bottom: 8px;
        }
        
        .tabs button {
          padding: 8px 16px;
          border: none;
          background: #f3f4f6;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          color: #6b7280;
          transition: all 0.2s;
        }
        
        .tabs button.active {
          background: #2563eb;
          color: white;
        }
        
        .alerts-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .alert-item {
          padding: 12px;
          border-radius: 8px;
          border-left: 4px solid;
        }
        
        .alert-item.critical {
          background: #fef2f2;
          border-left-color: #ef4444;
        }
        
        .alert-item.opportunity {
          background: #f0fdf4;
          border-left-color: #22c55e;
        }
        
        .alert-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }
        
        .alert-header .icon { font-size: 16px; }
        .alert-header .name { font-weight: 600; color: #111827; }
        .alert-header .brand { color: #6b7280; font-size: 13px; }
        
        .alert-details {
          display: flex;
          gap: 16px;
          margin-bottom: 8px;
          font-size: 13px;
          color: #6b7280;
        }
        
        .alert-message {
          font-size: 13px;
          color: #374151;
          margin-bottom: 8px;
        }
        
        .alert-action {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          font-weight: 500;
        }
        
        .alert-action .recommendation { color: #2563eb; }
        .alert-action .cost { color: #16a34a; }
        
        .empty-state {
          text-align: center;
          padding: 32px;
          color: #6b7280;
          font-size: 14px;
        }
        
        .sales-analysis .section {
          margin-bottom: 16px;
        }
        
        .sales-analysis h4 {
          font-size: 14px;
          margin: 0 0 8px 0;
          color: #374151;
        }
        
        .seller-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        
        .seller-list li {
          display: flex;
          justify-content: space-between;
          padding: 8px;
          background: #f9fafb;
          border-radius: 4px;
          margin-bottom: 4px;
          font-size: 13px;
        }
        
        .seller-list .rank {
          color: #f59e0b;
          font-weight: 600;
          width: 30px;
        }
        
        .seller-list .name { flex: 1; color: #111827; }
        .seller-list .sales { color: #16a34a; font-weight: 500; }
        .seller-list.low .stock { color: #ef4444; }
        
        .loading, .error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px;
          gap: 12px;
          color: #6b7280;
        }
        
        .spinner {
          width: 32px;
          height: 32px;
          border: 3px solid #e5e7eb;
          border-top-color: #2563eb;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .error button {
          margin-top: 8px;
          padding: 8px 16px;
          background: #2563eb;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        }
      `}</style>
        </div>
    );
}
