import React, { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import * as Lucide from "lucide-react";
import Sidebar from "../components/Sidebar";
import { ToastContainer, type ToastType } from "../components/Toast";
import api, { installmentAPI, customerAPI } from "../services/api";
import { useTranslation } from "react-i18next";

const {
    CreditCard = () => <span>💳</span>,
    ChevronRight = () => <span>→</span>,
    Search = () => <span>🔍</span>,
    Filter = () => <span>⚙</span>,
    CheckCircle = () => <span>✓</span>,
    Clock = () => <span>⏰</span>,
    AlertTriangle = () => <span>⚠</span>,
    XCircle = () => <span>✕</span>,
    Loader2 = () => <span>↻</span>,
    RefreshCw = () => <span>↺</span>,
    Plus = () => <span>+</span>,
    Ban = () => <span>🚫</span>,
    Phone = () => <span>📞</span>,
    Mail = () => <span>✉</span>,
    FileText = () => <span>📄</span>,
    Pencil = () => <span>✏</span>,
    Save = () => <span>💾</span>,
} = Lucide as any;

interface InstallmentPlan {
    id: number;
    customer: number;
    customer_name: string;
    product: number;
    product_name: string;
    total_amount: string;
    down_payment: string;
    installment_count: number;
    start_date: string;
    status: string;
    status_display: string;
    remaining_amount: string;
    paid_amount: string;
    progress_percentage: number;
    created_at: string;
    notes?: string;
}

interface CustomerDetail {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    phone_number?: string;
}

interface Installment {
    id: number;
    installment_number: number;
    amount: string;
    due_date: string;
    payment_date: string | null;
    status: string;
    status_display: string;
    is_overdue: boolean;
    days_until_due: number;
}

interface Toast {
    id: string;
    type: ToastType;
    message: string;
}

export default function InstallmentPlansPage() {
    const { t } = useTranslation();
    const [plans, setPlans] = useState<InstallmentPlan[]>([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedPlan, setSelectedPlan] = useState<InstallmentPlan | null>(null);
    const [installments, setInstallments] = useState<Installment[]>([]);
    const [detailLoading, setDetailLoading] = useState(false);
    const [toasts, setToasts] = useState<Toast[]>([]);
    const [approvingId, setApprovingId] = useState<number | null>(null);
    const [searchParams, setSearchParams] = useSearchParams();
    const [customerDetail, setCustomerDetail] = useState<CustomerDetail | null>(null);
    const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);
    const [cancellingPlan, setCancellingPlan] = useState(false);
    const [editingNotes, setEditingNotes] = useState(false);
    const [notesValue, setNotesValue] = useState("");
    const [savingNotes, setSavingNotes] = useState(false);

    // Taksit düzenleme state'i
    const [editingInstallmentId, setEditingInstallmentId] = useState<number | null>(null);
    const [editInstallmentForm, setEditInstallmentForm] = useState<{
        due_date: string;
        amount: string;
        payment_date: string;
        status: string;
    }>({ due_date: '', amount: '', payment_date: '', status: '' });
    const [savingInstallment, setSavingInstallment] = useState(false);

    // Creation Modal State
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [customers, setCustomers] = useState<any[]>([]);
    const [customerAssignments, setCustomerAssignments] = useState<any[]>([]);
    const [createForm, setCreateForm] = useState({
        customer: "",
        product: "",
        down_payment: "",
        installment_count: 9,
        start_date: new Date().toISOString().split('T')[0]
    });
    const [creating, setCreating] = useState(false);

    // Derived state for Total Amount - now from assignment's product
    const selectedAssignmentPrice = useMemo(() => {
        const assignment = customerAssignments.find(a => a.id === Number(createForm.product));
        return assignment?.product?.price || 0;
    }, [createForm.product, customerAssignments]);

    const fetchDropdowns = async () => {
        try {
            const custRes = await customerAPI.list({ role: 'customer', page_size: 1000 });
            setCustomers(custRes.data.results || custRes.data);
        } catch (error) {
            console.error("Error fetching customers:", error);
            showToast("error", t('installments.errCustomerList'));
        }
    };

    // Fetch customer's assigned products when customer is selected
    const fetchCustomerAssignments = async (customerId: number) => {
        try {
            const response = await api.get(`/assignments/?customer=${customerId}`);
            const assignments = response.data.results || response.data;
            // Filter to only PLANNED or SCHEDULED - not yet delivered
            const availableAssignments = assignments.filter((a: any) =>
                a.status === 'PLANNED' || a.status === 'SCHEDULED'
            );
            setCustomerAssignments(availableAssignments);
        } catch (error) {
            console.error("Error fetching assignments:", error);
            setCustomerAssignments([]);
        }
    };

    const handleOpenCreateModal = () => {
        setIsCreateModalOpen(true);
        fetchDropdowns();
    };

    const handleCreateSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setCreating(true);

        try {
            // Get assignment to send assignment_id instead of product_id
            const selectedAssignment = customerAssignments.find(a => a.id === Number(createForm.product));
            const payload = {
                customer: Number(createForm.customer),
                product: selectedAssignment?.product?.id, // product_id from nested product object
                assignment: Number(createForm.product), // assignment_id
                total_amount: selectedAssignmentPrice,
                down_payment: Number(createForm.down_payment) || 0,
                installment_count: Number(createForm.installment_count),
                start_date: createForm.start_date
            };

            await installmentAPI.createPlan(payload);
            showToast("success", t('installments.succCreated'));
            setIsCreateModalOpen(false);
            setCreateForm({
                customer: "", product: "", down_payment: "", installment_count: 9, start_date: new Date().toISOString().split('T')[0]
            });
            fetchPlans();
        } catch (error: any) {
            console.error("Create plan error:", error);
            showToast("error", error.response?.data?.detail || t('installments.errCreate'));
        } finally {
            setCreating(false);
        }
    };

    const fetchPlans = async () => {
        setLoading(true);
        try {
            const filters = statusFilter !== "all" ? { status: statusFilter } : undefined;
            const response = await installmentAPI.getAllPlans(filters);
            // Handle pagination (DRF usually returns { results: [...] })
            const data = response.data;
            setPlans(Array.isArray(data) ? data : (data.results || []));
        } catch (error: any) {
            console.error("Failed to fetch plans:", error);
            showToast("error", t('installments.errList'));
        } finally {
            setLoading(false);
        }
    };

    const fetchInstallments = async (planId: number) => {
        setDetailLoading(true);
        try {
            const response = await installmentAPI.getPlanInstallments(planId);
            // Handle pagination
            const data = response.data;
            setInstallments(Array.isArray(data) ? data : (data.results || []));
        } catch (error: any) {
            console.error("Failed to fetch installments:", error);
            showToast("error", t('installments.errInstList'));
        } finally {
            setDetailLoading(false);
        }
    };

    useEffect(() => {
        fetchPlans();
    }, [statusFilter]);

    const showToast = (type: ToastType, message: string) => {
        const id = Date.now().toString();
        setToasts(prev => [...prev, { id, type, message }]);
    };

    const removeToast = (id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    const handleViewDetail = (plan: InstallmentPlan) => {
        setSearchParams({ planId: plan.id.toString() });
    };

    const handleBackToList = () => {
        setSearchParams({});
        setSelectedPlan(null);
        setInstallments([]);
        setCustomerDetail(null);
        setEditingNotes(false);
        setCancelConfirmOpen(false);
    };

    useEffect(() => {
        const planId = searchParams.get("planId");
        if (planId) {
            const loadDetail = async () => {
                // Eğer zaten yüklüyse tekrar yükleme
                if (selectedPlan && selectedPlan.id === Number(planId)) return;

                setLoading(true);
                try {
                    // Plan detayını çek (listeden bağımsız)
                    const response = await installmentAPI.getPlan(Number(planId));
                    const plan = response.data;
                    setSelectedPlan(plan);
                    setNotesValue(plan.notes || "");
                    // Müşteri bilgisini çek
                    try {
                        const custRes = await customerAPI.get(plan.customer);
                        setCustomerDetail(custRes.data);
                    } catch {
                        setCustomerDetail(null);
                    }
                    // Taksitleri çek
                    await fetchInstallments(Number(planId));
                } catch (error) {
                    console.error("Plan detay hatası:", error);
                    showToast("error", t('installments.errDetail'));
                    setSearchParams({}); // Hatada listeye dön
                } finally {
                    setLoading(false);
                }
            };
            loadDetail();
        } else {
            // URL parametresi yoksa detaydan çık
            setSelectedPlan(null);
            setInstallments([]);
        }
    }, [searchParams]);

    const handleApprovePayment = async (installmentId: number) => {
        setApprovingId(installmentId);
        try {
            await installmentAPI.adminApprovePayment(installmentId);
            showToast("success", t('installments.succApproved'));
            if (selectedPlan) {
                fetchInstallments(selectedPlan.id);
                fetchPlans(); // Refresh list to update progress
            }
        } catch (error: any) {
            console.error("Failed to approve payment:", error);
            showToast("error", t('installments.errApprove'));
        } finally {
            setApprovingId(null);
        }
    };

    const handleStartEditInstallment = (inst: Installment) => {
        setEditingInstallmentId(inst.id);
        setEditInstallmentForm({
            due_date: inst.due_date,
            amount: inst.amount,
            payment_date: inst.payment_date || '',
            status: inst.status,
        });
    };

    const handleSaveInstallment = async (installmentId: number) => {
        setSavingInstallment(true);
        try {
            const payload: any = {
                due_date: editInstallmentForm.due_date,
                amount: editInstallmentForm.amount,
                status: editInstallmentForm.status,
            };
            if (editInstallmentForm.payment_date) {
                payload.payment_date = editInstallmentForm.payment_date;
            } else {
                payload.payment_date = null;
            }
            await installmentAPI.updateInstallment(installmentId, payload);
            showToast("success", t('installments.succUpdated'));
            setEditingInstallmentId(null);
            if (selectedPlan) {
                fetchInstallments(selectedPlan.id);
                fetchPlans();
            }
        } catch (error: any) {
            showToast("error", error.response?.data?.detail || t('installments.errUpdate'));
        } finally {
            setSavingInstallment(false);
        }
    };

    const handleCancelPlan = async () => {
        if (!selectedPlan) return;
        setCancellingPlan(true);
        try {
            await installmentAPI.cancelPlan(selectedPlan.id);
            setSelectedPlan({ ...selectedPlan, status: 'cancelled', status_display: t('installments.filterCancelled') });
            setCancelConfirmOpen(false);
            showToast("success", t('installments.succCancelled'));
            fetchPlans();
        } catch (error: any) {
            showToast("error", error.response?.data?.detail || t('installments.errCancel'));
        } finally {
            setCancellingPlan(false);
        }
    };

    const handleSaveNotes = async () => {
        if (!selectedPlan) return;
        setSavingNotes(true);
        try {
            await installmentAPI.updatePlanNotes(selectedPlan.id, notesValue);
            setSelectedPlan({ ...selectedPlan, notes: notesValue });
            setEditingNotes(false);
            showToast("success", t('installments.succNote'));
        } catch (error: any) {
            showToast("error", t('installments.errNote'));
        } finally {
            setSavingNotes(false);
        }
    };

    const filteredPlans = useMemo(() => {
        return plans.filter(plan => {
            const matchesSearch =
                plan.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                plan.product_name.toLowerCase().includes(searchTerm.toLowerCase());
            return matchesSearch;
        });
    }, [plans, searchTerm]);

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "active": return <Clock className="w-4 h-4 text-blue-500" />;
            case "completed": return <CheckCircle className="w-4 h-4 text-green-500" />;
            case "cancelled": return <XCircle className="w-4 h-4 text-gray-500" />;
            default: return null;
        }
    };

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case "active": return "bg-blue-100 text-blue-800";
            case "completed": return "bg-green-100 text-green-800";
            case "cancelled": return "bg-gray-100 text-gray-800";
            case "pending": return "bg-yellow-100 text-yellow-800";
            case "customer_confirmed": return "bg-purple-100 text-purple-800";
            case "paid": return "bg-green-100 text-green-800";
            case "overdue": return "bg-red-100 text-red-800";
            default: return "bg-gray-100 text-gray-800";
        }
    };

    const formatCurrency = (amount: string) => {
        return parseFloat(amount).toLocaleString("tr-TR", { minimumFractionDigits: 2 }) + " ₺";
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" });
    };

    // Detail View
    if (selectedPlan) {
        return (
            <div className="flex min-h-screen bg-gray-100">
                <Sidebar />
                <main className="flex-1 p-6">
                    <button
                        onClick={handleBackToList}
                        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
                    >
                        {t('installments.btnBack')}
                    </button>

                    <div className="bg-white rounded-xl shadow-md p-6 mb-6">
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">{selectedPlan.product_name}</h1>
                                <div className="flex items-center gap-4 mt-1 flex-wrap">
                                    <p className="text-gray-600">{t('installments.lblCustomer')}<span className="font-medium">{selectedPlan.customer_name}</span></p>
                                    {customerDetail?.phone_number && (
                                        <span className="flex items-center gap-1 text-sm text-gray-500">
                                            <Phone className="w-3 h-3" />
                                            {customerDetail.phone_number}
                                        </span>
                                    )}
                                    {customerDetail?.email && (
                                        <span className="flex items-center gap-1 text-sm text-gray-500">
                                            <Mail className="w-3 h-3" />
                                            {customerDetail.email}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadgeClass(selectedPlan.status)}`}>
                                    {selectedPlan.status_display}
                                </span>
                                {selectedPlan.status === 'active' && (
                                    <button
                                        onClick={() => setCancelConfirmOpen(true)}
                                        data-testid="cancel-plan-btn"
                                        className="flex items-center gap-1 px-3 py-1 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm font-medium"
                                    >
                                        <Ban className="w-4 h-4" />
                                        {t('installments.btnCancel')}
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-4 gap-4 mb-4">
                            <div className="text-center p-4 bg-gray-50 rounded-lg">
                                <div className="text-sm text-gray-500">{t('installments.kpiTotal')}</div>
                                <div className="text-lg font-bold">{formatCurrency(selectedPlan.total_amount)}</div>
                            </div>
                            <div className="text-center p-4 bg-gray-50 rounded-lg">
                                <div className="text-sm text-gray-500">{t('installments.kpiDownPayment')}</div>
                                <div className="text-lg font-bold">{formatCurrency(selectedPlan.down_payment)}</div>
                            </div>
                            <div className="text-center p-4 bg-green-50 rounded-lg">
                                <div className="text-sm text-green-600">{t('installments.kpiPaid')}</div>
                                <div className="text-lg font-bold text-green-700">{formatCurrency(selectedPlan.paid_amount)}</div>
                            </div>
                            <div className="text-center p-4 bg-red-50 rounded-lg">
                                <div className="text-sm text-red-600">{t('installments.kpiRemaining')}</div>
                                <div className="text-lg font-bold text-red-700">{formatCurrency(selectedPlan.remaining_amount)}</div>
                            </div>
                        </div>

                        <div className="flex items-center gap-4 mb-4">
                            <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-green-500 transition-all duration-500"
                                    style={{ width: `${selectedPlan.progress_percentage}%` }}
                                />
                            </div>
                            <span className="text-lg font-bold">{selectedPlan.progress_percentage}%</span>
                        </div>

                        {/* Not Bölümü */}
                        <div className="border-t border-gray-100 pt-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="flex items-center gap-1 text-sm font-medium text-gray-600">
                                    <FileText className="w-4 h-4" /> {t('installments.lblNote')}
                                </span>
                                {!editingNotes && selectedPlan.status !== 'cancelled' && (
                                    <button
                                        data-testid="notes-edit-btn"
                                        onClick={() => { setEditingNotes(true); setNotesValue(selectedPlan.notes || ""); }}
                                        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800"
                                    >
                                        <Pencil className="w-3 h-3" /> {t('installments.btnEdit')}
                                    </button>
                                )}
                            </div>
                            {editingNotes ? (
                                <div className="flex gap-2">
                                    <textarea
                                        data-testid="notes-textarea"
                                        value={notesValue}
                                        onChange={e => setNotesValue(e.target.value)}
                                        rows={2}
                                        className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-black focus:border-transparent resize-none"
                                        placeholder={t('installments.placeholderNote')}
                                    />
                                    <div className="flex flex-col gap-1">
                                        <button
                                            onClick={handleSaveNotes}
                                            disabled={savingNotes}
                                            data-testid="save-notes-btn"
                                            className="flex items-center gap-1 px-3 py-1 bg-black text-white rounded-lg text-sm disabled:opacity-50"
                                        >
                                            <Save className="w-3 h-3" /> {savingNotes ? "..." : t('installments.btnSave')}
                                        </button>
                                        <button
                                            onClick={() => setEditingNotes(false)}
                                            className="px-3 py-1 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                                        >
                                            {t('installments.btnCancelEdit')}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <p className="text-sm text-gray-500 italic">
                                    {selectedPlan.notes || t('installments.noNote')}
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="bg-white rounded-xl shadow-md p-6">
                        <h2 className="text-xl font-bold mb-4">{t('installments.titleInstallments')}</h2>

                        {detailLoading ? (
                            <div className="flex justify-center py-12">
                                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                            </div>
                        ) : (
                            <table className="w-full">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">{t('installments.colInstNo')}</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">{t('installments.colAmount')}</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">{t('installments.colDueDate')}</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">{t('installments.colPayDate')}</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">{t('installments.colStatus')}</th>
                                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">{t('installments.colAction')}</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                    {installments.map((inst) => {
                                        const isOverdue = inst.is_overdue;
                                        const daysAbs = Math.abs(inst.days_until_due);
                                        let daysLabel = "";
                                        if (inst.status !== 'paid' && inst.status !== 'customer_confirmed') {
                                            if (isOverdue) daysLabel = t('installments.daysOverdue', { days: daysAbs });
                                            else if (inst.days_until_due === 0) daysLabel = t('installments.todayDue');
                                            else daysLabel = t('installments.daysLeft', { days: inst.days_until_due });
                                        }
                                        const isEditing = editingInstallmentId === inst.id;
                                        return (
                                            <tr
                                                key={inst.id}
                                                data-testid={`installment-row-${inst.id}`}
                                                className={isOverdue ? "bg-red-50 border-l-4 border-red-500" : ""}
                                            >
                                                <td className="px-4 py-4">
                                                    <span className={`inline-flex items-center justify-center w-8 h-8 ${isOverdue ? 'bg-red-600' : 'bg-gray-900'} text-white rounded-full font-bold text-sm`}>
                                                        {inst.installment_number}
                                                    </span>
                                                </td>
                                                {/* Tutar */}
                                                <td className="px-4 py-4 font-medium">
                                                    {isEditing ? (
                                                        <input
                                                            type="number"
                                                            step="0.01"
                                                            value={editInstallmentForm.amount}
                                                            onChange={e => setEditInstallmentForm(f => ({ ...f, amount: e.target.value }))}
                                                            className="w-28 border border-gray-300 rounded px-2 py-1 text-sm"
                                                        />
                                                    ) : formatCurrency(inst.amount)}
                                                </td>
                                                {/* Vade Tarihi */}
                                                <td className="px-4 py-4">
                                                    {isEditing ? (
                                                        <input
                                                            type="date"
                                                            value={editInstallmentForm.due_date}
                                                            onChange={e => setEditInstallmentForm(f => ({ ...f, due_date: e.target.value }))}
                                                            className="border border-gray-300 rounded px-2 py-1 text-sm"
                                                        />
                                                    ) : (
                                                        <>
                                                            <div>{formatDate(inst.due_date)}</div>
                                                            {daysLabel && (
                                                                <div className={`text-xs mt-0.5 font-medium ${isOverdue ? 'text-red-600' : 'text-amber-600'}`}>
                                                                    {daysLabel}
                                                                </div>
                                                            )}
                                                        </>
                                                    )}
                                                </td>
                                                {/* Ödeme Tarihi */}
                                                <td className="px-4 py-4">
                                                    {isEditing ? (
                                                        <input
                                                            type="date"
                                                            value={editInstallmentForm.payment_date}
                                                            onChange={e => setEditInstallmentForm(f => ({ ...f, payment_date: e.target.value }))}
                                                            className="border border-gray-300 rounded px-2 py-1 text-sm"
                                                        />
                                                    ) : (inst.payment_date ? formatDate(inst.payment_date) : "-")}
                                                </td>
                                                {/* Durum */}
                                                <td className="px-4 py-4">
                                                    {isEditing ? (
                                                        <select
                                                            value={editInstallmentForm.status}
                                                            onChange={e => setEditInstallmentForm(f => ({ ...f, status: e.target.value }))}
                                                            className="border border-gray-300 rounded px-2 py-1 text-sm"
                                                        >
                                                            <option value="pending">{t('installments.statusPending')}</option>
                                                            <option value="customer_confirmed">{t('installments.statusCustomerConfirmed')}</option>
                                                            <option value="paid">{t('installments.statusPaid')}</option>
                                                            <option value="overdue">{t('installments.statusOverdue')}</option>
                                                        </select>
                                                    ) : (
                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeClass(inst.status)}`}>
                                                            {inst.status_display}
                                                        </span>
                                                    )}
                                                </td>
                                                {/* İşlem Butonları */}
                                                <td className="px-4 py-4 text-right">
                                                    {isEditing ? (
                                                        <div className="flex gap-2 justify-end">
                                                            <button
                                                                onClick={() => handleSaveInstallment(inst.id)}
                                                                disabled={savingInstallment}
                                                                className="px-3 py-1 bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 text-sm"
                                                            >
                                                                {savingInstallment ? "..." : t('installments.btnSave')}
                                                            </button>
                                                            <button
                                                                onClick={() => setEditingInstallmentId(null)}
                                                                className="px-3 py-1 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 text-sm"
                                                            >
                                                                {t('installments.btnCancelEdit')}
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="flex gap-2 justify-end">
                                                            {inst.status === "customer_confirmed" && (
                                                                <button
                                                                    onClick={() => handleApprovePayment(inst.id)}
                                                                    disabled={approvingId === inst.id}
                                                                    className="px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm"
                                                                >
                                                                    {approvingId === inst.id ? "..." : t('installments.btnApprove')}
                                                                </button>
                                                            )}
                                                            <button
                                                                onClick={() => handleStartEditInstallment(inst)}
                                                                className="px-3 py-1 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 text-sm flex items-center gap-1"
                                                            >
                                                                <Pencil />
                                                                {t('installments.btnEdit')}
                                                            </button>
                                                        </div>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* İptal Onay Modalı */}
                    {cancelConfirmOpen && (
                        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                            <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
                                <h3 className="text-lg font-bold text-gray-900 mb-2">{t('installments.titleCancelPlan')}</h3>
                                <p className="text-gray-600 text-sm mb-6" dangerouslySetInnerHTML={{ __html: t('installments.descCancelPlan', { product: selectedPlan?.product_name }) }} />
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => setCancelConfirmOpen(false)}
                                        className="flex-1 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium text-sm"
                                    >
                                        {t('installments.btnCancelEdit')}
                                    </button>
                                    <button
                                        onClick={handleCancelPlan}
                                        disabled={cancellingPlan}
                                        data-testid="confirm-cancel-btn"
                                        className="flex-1 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 font-medium text-sm"
                                    >
                                        {cancellingPlan ? "..." : t('installments.btnConfirmCancel')}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    <ToastContainer toasts={toasts} onRemove={removeToast} />
                </main>
            </div>
        );
    }

    // List View
    return (
        <div className="flex min-h-screen bg-gray-100">
            <Sidebar />
            <main className="flex-1 p-6">
                <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-3">
                        <CreditCard className="w-8 h-8 text-gray-700" />
                        <h1 className="text-2xl font-bold text-gray-900">{t('installments.title')}</h1>
                    </div>
                    <button
                        onClick={fetchPlans}
                        className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900"
                    >
                        <RefreshCw className="w-4 h-4" />
                        {t('installments.btnRefresh')}
                    </button>
                    <button
                        onClick={handleOpenCreateModal}
                        className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800"
                    >
                        <Plus className="w-4 h-4" />
                        {t('installments.btnNewPlan')}
                    </button>
                </div>

                {/* Filters */}
                <div className="flex gap-4 mb-6">
                    <div className="flex-1 relative">
                        <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder={t('installments.searchPlaceholder')}
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                    </div>
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black"
                    >
                        <option value="all">{t('installments.filterAll')}</option>
                        <option value="active">{t('installments.filterActive')}</option>
                        <option value="completed">{t('installments.filterCompleted')}</option>
                        <option value="cancelled">{t('installments.filterCancelled')}</option>
                    </select>
                </div>

                {/* Plans Table */}
                <div className="bg-white rounded-xl shadow-md overflow-hidden">
                    {loading ? (
                        <div className="flex justify-center py-12">
                            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                        </div>
                    ) : filteredPlans.length === 0 ? (
                        <div className="text-center py-12">
                            <CreditCard className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                            <p className="text-gray-500">{t('installments.noPlans')}</p>
                        </div>
                    ) : (
                        <table className="w-full">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">{t('installments.colCustomer')}</th>
                                    <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">{t('installments.colProduct')}</th>
                                    <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">{t('installments.colTotal')}</th>
                                    <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">{t('installments.colRemaining')}</th>
                                    <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">{t('installments.colProgress')}</th>
                                    <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">{t('installments.colStatus')}</th>
                                    <th className="px-6 py-4 text-right text-sm font-medium text-gray-600">{t('installments.colAction')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {filteredPlans.map((plan) => (
                                    <tr key={plan.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4 font-medium">{plan.customer_name}</td>
                                        <td className="px-6 py-4 text-gray-600">{plan.product_name}</td>
                                        <td className="px-6 py-4">{formatCurrency(plan.total_amount)}</td>
                                        <td className="px-6 py-4 text-red-600 font-medium">{formatCurrency(plan.remaining_amount)}</td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-green-500"
                                                        style={{ width: `${plan.progress_percentage}%` }}
                                                    />
                                                </div>
                                                <span className="text-sm font-medium">{plan.progress_percentage}%</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeClass(plan.status)}`}>
                                                {getStatusIcon(plan.status)}
                                                {plan.status_display}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button
                                                onClick={() => handleViewDetail(plan)}
                                                className="px-4 py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                                            >
                                                Detay
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Create Modal */}
                {isCreateModalOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                        <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl overflow-hidden">
                            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                                <h3 className="font-bold text-gray-900">{t('installments.modalTitle')}</h3>
                                <button onClick={() => setIsCreateModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                                    <XCircle className="w-6 h-6" />
                                </button>
                            </div>

                            <form onSubmit={handleCreateSubmit} className="p-6 space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('installments.lblCustomerSelect')}</label>
                                    <select
                                        required
                                        className="w-full border-gray-300 rounded-lg focus:ring-black focus:border-black"
                                        value={createForm.customer}
                                        onChange={e => {
                                            const customerId = e.target.value;
                                            setCreateForm({ ...createForm, customer: customerId, product: "" });
                                            if (customerId) {
                                                fetchCustomerAssignments(Number(customerId));
                                            } else {
                                                setCustomerAssignments([]);
                                            }
                                        }}
                                    >
                                        <option value="">{t('installments.optSelect', { defaultValue: 'Seçiniz' })}</option>
                                        {customers.map((c: any) => (
                                            <option key={c.id} value={c.id}>{c.first_name} {c.last_name} ({c.email})</option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('installments.lblProductSelect', { defaultValue: 'Atanmış Ürün' })}</label>
                                    <select
                                        required
                                        disabled={!createForm.customer}
                                        className="w-full border-gray-300 rounded-lg focus:ring-black focus:border-black disabled:bg-gray-100"
                                        value={createForm.product}
                                        onChange={e => setCreateForm({ ...createForm, product: e.target.value })}
                                    >
                                        <option value="">{createForm.customer ? t('installments.optSelectAssigned', { defaultValue: 'Atanmış ürün seçiniz' }) : t('installments.optSelectCustomerFirst', { defaultValue: 'Önce müşteri seçin' })}</option>
                                        {customerAssignments.map((a: any) => (
                                            <option key={a.id} value={a.id}>
                                                {a.product?.name} - {a.product?.price} TL ({a.status_display})
                                            </option>
                                        ))}
                                    </select>
                                    {createForm.customer && customerAssignments.length === 0 && (
                                        <p className="text-xs text-orange-600 mt-1">{t('installments.noAssignedProduct', { defaultValue: 'Bu müşteriye atanmış ürün bulunmuyor' })}</p>
                                    )}
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">{t('installments.lblTotalAmount')}</label>
                                        <input
                                            type="text"
                                            disabled
                                            value={`${selectedAssignmentPrice} TL`}
                                            className="w-full bg-gray-100 border-gray-300 rounded-lg text-gray-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">{t('installments.lblDownPayment')}</label>
                                        <input
                                            type="number"
                                            min="0"
                                            max={selectedAssignmentPrice}
                                            required
                                            className="w-full border-gray-300 rounded-lg focus:ring-black focus:border-black"
                                            value={createForm.down_payment}
                                            onChange={e => setCreateForm({ ...createForm, down_payment: e.target.value })}
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">{t('installments.lblInstallmentCount')}</label>
                                        <select
                                            className="w-full border-gray-300 rounded-lg focus:ring-black focus:border-black"
                                            value={createForm.installment_count}
                                            onChange={e => setCreateForm({ ...createForm, installment_count: Number(e.target.value) })}
                                        >
                                            {[3, 6, 9, 12, 18, 24].map(n => (
                                                <option key={n} value={n}>{n} {t('installments.installments', { defaultValue: 'Taksit' })}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">{t('installments.lblStartDate')}</label>
                                        <input
                                            type="date"
                                            required
                                            className="w-full border-gray-300 rounded-lg focus:ring-black focus:border-black"
                                            value={createForm.start_date}
                                            onChange={e => setCreateForm({ ...createForm, start_date: e.target.value })}
                                        />
                                    </div>
                                </div>

                                <div className="pt-4 flex gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setIsCreateModalOpen(false)}
                                        className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 font-medium"
                                    >
                                        {t('installments.btnCancelEdit')}
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={creating}
                                        className="flex-1 py-2.5 bg-black text-white rounded-xl hover:bg-gray-800 font-medium disabled:opacity-50"
                                    >
                                        {creating ? t('installments.btnCreateLoading') : t('installments.btnCreate')}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                <ToastContainer toasts={toasts} onRemove={removeToast} />
            </main>
        </div>
    );
}
