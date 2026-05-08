import React, { useEffect, useState } from "react";
import * as Lucide from "lucide-react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { ToastContainer, type ToastType } from "../components/Toast";
import api from "../services/api";
import { useTranslation } from "react-i18next";

const {
    Bell = () => <span>🔔</span>,
    Send = () => <span>📤</span>,
    Users = () => <span>👥</span>,
    X = () => <span>✕</span>,
    Loader2 = () => <span>↻</span>,
    CheckCircle = () => <span>✓</span>,
    Tag = () => <span>🏷</span>,
    Megaphone = () => <span>📢</span>,
    Settings = () => <span>⚙️</span>,
    Search = () => <span>🔍</span>,
    Filter = () => <span>📋</span>,
} = Lucide as any;

interface NotificationRecord {
    id: number;
    user: { id: number; username: string; email: string };
    notification_type: string;
    title: string;
    message: string;
    is_read: boolean;
    created_at: string;
}

const NotificationTypeLabels: Record<string, { label: string; color: string }> = {
    general: { label: "Genel", color: "bg-blue-100 text-blue-700" },
    price_drop: { label: "Fiyat Düşüşü", color: "bg-green-100 text-green-700" },
    restock: { label: "Stok Geldi", color: "bg-purple-100 text-purple-700" },
    service_update: { label: "Servis", color: "bg-orange-100 text-orange-700" },
    recommendation: { label: "Öneri", color: "bg-yellow-100 text-yellow-700" },
    warranty_expiry: { label: "Garanti", color: "bg-red-100 text-red-700" },
};

export default function NotificationsPage() {
    const { t } = useTranslation();
    const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    // Since NotificationTypeLabels is defined outside the component, we can use the translation inside the render loop, but for cleaner code we can compute them inside the component:
    const notificationTypeLabels: Record<string, { label: string; color: string }> = {
        general: { label: t('notifications.typeGeneral'), color: "bg-blue-100 text-blue-700" },
        price_drop: { label: t('notifications.typePriceDrop'), color: "bg-green-100 text-green-700" },
        restock: { label: t('notifications.typeRestock'), color: "bg-purple-100 text-purple-700" },
        service_update: { label: t('notifications.typeService'), color: "bg-orange-100 text-orange-700" },
        recommendation: { label: t('notifications.typeRecommendation'), color: "bg-yellow-100 text-yellow-700" },
        warranty_expiry: { label: t('notifications.typeWarranty'), color: "bg-red-100 text-red-700" },
    };

    // Filter & Search
    const [searchQuery, setSearchQuery] = useState("");
    const [filterType, setFilterType] = useState("all");

    // Modal state
    const [modalOpen, setModalOpen] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    // Form state
    const [title, setTitle] = useState("");
    const [message, setMessage] = useState("");
    const [notificationType, setNotificationType] = useState("general");
    const [target, setTarget] = useState<"all" | "customers">("customers");

    // Toast
    const [toasts, setToasts] = useState<Array<{ id: string; type: ToastType; message: string }>>([]);

    const token = localStorage.getItem("access");

    // Filtered notifications
    const filteredNotifications = notifications.filter((n) => {
        const matchesSearch = searchQuery === "" ||
            n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            n.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
            n.user?.email?.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesType = filterType === "all" || n.notification_type === filterType;
        return matchesSearch && matchesType;
    });

    useEffect(() => {
        fetchNotifications();
    }, []);

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            const res = await api.get("/notifications/all/");
            setNotifications(Array.isArray(res.data) ? res.data : []);
        } catch (error) {
            showToast("error", t('notifications.errFetch'));
        } finally {
            setLoading(false);
        }
    };

    const showToast = (type: ToastType, message: string) => {
        const id = Date.now().toString();
        setToasts((prev) => [...prev, { id, type, message }]);
    };

    const removeToast = (id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    const handleSubmit = async () => {
        if (!title.trim() || !message.trim()) {
            showToast("error", t('notifications.valTitleMsgReq'));
            return;
        }

        setSubmitting(true);
        try {
            const res = await api.post("/notifications/send-bulk/", {
                title,
                message,
                notification_type: notificationType,
                target,
            });

            showToast("success", res.data.success);
            setModalOpen(false);
            resetForm();
            fetchNotifications();
        } catch (error: any) {
            const errData = error.response?.data;
            showToast("error", errData?.error || error.message || t('notifications.errDefault'));
        } finally {
            setSubmitting(false);
        }
    };

    const resetForm = () => {
        setTitle("");
        setMessage("");
        setNotificationType("general");
        setTarget("customers");
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString("tr-TR", {
            day: "numeric",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    if (loading) {
        return (
            <div className="flex min-h-screen bg-gray-50">
                <Sidebar />
                <div className="flex-1 flex items-center justify-center">
                    <Loader2 className="animate-spin" />
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen bg-gray-50">
            <Sidebar />
            <ToastContainer toasts={toasts} onRemove={removeToast} />

            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Header */}
                <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
                    <div className="px-6 py-4 flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div className="p-2 bg-purple-100 rounded-lg">
                                <Bell className="w-5 h-5 text-purple-600" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-gray-900">{t('notifications.title')}</h1>
                                <p className="text-sm text-gray-500">{t('notifications.subtitle')}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => navigate("/dashboard/notifications/preferences")}
                                className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700"
                            >
                                <Settings className="w-4 h-4" />
                                {t('notifications.btnPrefs')}
                            </button>
                            <button
                                onClick={() => setModalOpen(true)}
                                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors font-medium flex items-center gap-2"
                            >
                                <Send className="w-4 h-4" />
                                {t('notifications.btnSend')}
                            </button>
                        </div>
                    </div>

                    {/* Search and Filter Bar */}
                    <div className="px-6 py-3 border-t border-gray-100 flex items-center gap-4">
                        <div className="flex-1 relative">
                            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                            <input
                                type="text"
                                placeholder={t('notifications.searchPlaceholder')}
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none text-sm"
                            />
                        </div>
                        <select
                            value={filterType}
                            onChange={(e) => setFilterType(e.target.value)}
                            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none text-sm"
                        >
                            <option value="all">{t('notifications.filterAll')}</option>
                            <option value="general">{t('notifications.typeGeneral')}</option>
                            <option value="price_drop">{t('notifications.typePriceDrop')}</option>
                            <option value="restock">{t('notifications.typeRestock')}</option>
                            <option value="service_update">{t('notifications.typeService')}</option>
                            <option value="recommendation">{t('notifications.typeRecommendation')}</option>
                            <option value="warranty_expiry">{t('notifications.typeWarranty')}</option>
                        </select>
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 overflow-y-auto p-6">
                    <div className="max-w-[1200px] mx-auto space-y-6">
                        {/* Stats */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="bg-white rounded-xl border border-gray-200 p-4">
                                <p className="text-sm text-gray-600 mb-1">{t('notifications.statTotal')}</p>
                                <p className="text-3xl font-bold text-gray-900">{filteredNotifications.length}</p>
                            </div>
                            <div className="bg-white rounded-xl border border-gray-200 p-4">
                                <p className="text-sm text-gray-600 mb-1">{t('notifications.statRead')}</p>
                                <p className="text-3xl font-bold text-green-600">
                                    {filteredNotifications.filter((n) => n.is_read).length}
                                </p>
                            </div>
                            <div className="bg-white rounded-xl border border-gray-200 p-4">
                                <p className="text-sm text-gray-600 mb-1">{t('notifications.statUnread')}</p>
                                <p className="text-3xl font-bold text-orange-600">
                                    {filteredNotifications.filter((n) => !n.is_read).length}
                                </p>
                            </div>
                        </div>

                        {/* Recent Notifications */}
                        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                                <span className="text-sm font-medium text-gray-700">{t('notifications.recentTitle')}</span>
                                <span className="text-xs text-gray-500">{t('notifications.recentSubtitle')}</span>
                            </div>

                            {notifications.length === 0 ? (
                                <div className="px-4 py-12 text-center text-gray-500">
                                    <Megaphone className="mx-auto mb-2 text-4xl" />
                                    <p className="font-medium">{t('notifications.noNotifs')}</p>
                                    <p className="text-sm mt-1">{t('notifications.noNotifsDesc')}</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-gray-200 max-h-[500px] overflow-y-auto">
                                    {filteredNotifications.map((notif) => {
                                        const typeConfig = NotificationTypeLabels[notif.notification_type] || NotificationTypeLabels.general;
                                        return (
                                            <div key={notif.id} className="px-4 py-3 hover:bg-gray-50 transition-colors">
                                                <div className="flex items-start justify-between">
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${typeConfig.color}`}>
                                                                {typeConfig.label}
                                                            </span>
                                                            {notif.is_read ? (
                                                                <CheckCircle className="w-4 h-4 text-green-500" />
                                                            ) : (
                                                                <span className="w-2 h-2 bg-blue-500 rounded-full" />
                                                            )}
                                                        </div>
                                                        <p className="font-medium text-gray-900">{notif.title}</p>
                                                        <p className="text-sm text-gray-600 line-clamp-2">{notif.message}</p>
                                                        <p className="text-xs text-gray-400 mt-1">
                                                            → {notif.user?.email || t('notifications.unknownUser')} • {formatDate(notif.created_at)}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                </main>
            </div>

            {/* Send Notification Modal */}
            {modalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl w-full max-w-lg mx-4 shadow-2xl">
                        <div className="flex items-center justify-between p-4 border-b border-gray-200">
                            <h2 className="text-lg font-bold text-gray-900">{t('notifications.modalTitle')}</h2>
                            <button onClick={() => setModalOpen(false)} className="p-1 hover:bg-gray-100 rounded">
                                <X />
                            </button>
                        </div>

                        <div className="p-4 space-y-4">
                            {/* Title */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    {t('notifications.lblTitle')} <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder={t('notifications.plcTitle')}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none"
                                />
                            </div>

                            {/* Message */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    {t('notifications.lblMessage')} <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    placeholder={t('notifications.plcMessage')}
                                    rows={4}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none resize-none"
                                />
                            </div>

                            {/* Notification Type */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">{t('notifications.lblType')}</label>
                                <select
                                    value={notificationType}
                                    onChange={(e) => setNotificationType(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none"
                                >
                                    <option value="general">{t('notifications.typeGeneral')}</option>
                                    <option value="price_drop">{t('notifications.typePriceDrop')}</option>
                                    <option value="restock">{t('notifications.typeRestock')}</option>
                                    <option value="recommendation">{t('notifications.typeRecommendation')}</option>
                                </select>
                            </div>

                            {/* Target Audience */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">{t('notifications.lblTarget')}</label>
                                <div className="flex gap-3">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="radio"
                                            name="target"
                                            value="customers"
                                            checked={target === "customers"}
                                            onChange={() => setTarget("customers")}
                                            className="w-4 h-4 text-purple-600"
                                        />
                                        <span className="text-sm">{t('notifications.targetCustomers')}</span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="radio"
                                            name="target"
                                            value="all"
                                            checked={target === "all"}
                                            onChange={() => setTarget("all")}
                                            className="w-4 h-4 text-purple-600"
                                        />
                                        <span className="text-sm">{t('notifications.targetAll')}</span>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
                            <button
                                onClick={() => setModalOpen(false)}
                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium"
                            >
                                {t('notifications.btnCancel')}
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={submitting}
                                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 text-sm font-medium flex items-center gap-2"
                            >
                                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                <Send className="w-4 h-4" />
                                {t('notifications.btnSubmit')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
