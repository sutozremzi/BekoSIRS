import React, { useEffect, useState, useMemo } from "react";
import * as Lucide from "lucide-react";
import Sidebar from "../components/Sidebar";
import { ToastContainer, type ToastType } from "../components/Toast";
import api from "../services/api";

const {
    Package = () => <span>📦</span>,
    Users = () => <span>👥</span>,
    Plus = () => <span>+</span>,
    Search = () => <span>🔍</span>,
    Calendar = () => <span>📅</span>,
    Shield = () => <span>🛡️</span>,
    X = () => <span>✕</span>,
    Trash2 = () => <span>🗑</span>,
    Loader2 = () => <span>↻</span>,
    AlertCircle = () => <span>⚠</span>,
    CheckCircle = () => <span>✓</span>,
} = Lucide as any;

interface Customer {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
}

interface Product {
    id: number;
    name: string;
    brand: string;
    model_code?: string;
    category?: { name: string };
}

interface ProductOwnership {
    id: number;
    customer: Customer;
    product: Product;
    purchase_date: string;
    serial_number?: string;
    warranty_end_date?: string;
}

export default function AssignmentsPage() {
    const [ownerships, setOwnerships] = useState<ProductOwnership[]>([]);
    const [customers, setCustomers] = useState<Customer[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");

    // Modal state
    const [modalOpen, setModalOpen] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    // Form state
    const [selectedCustomer, setSelectedCustomer] = useState<number | "">("");
    const [selectedProduct, setSelectedProduct] = useState<number | "">("");
    const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().split("T")[0]);
    const [serialNumber, setSerialNumber] = useState("");

    // Toast
    const [toasts, setToasts] = useState<Array<{ id: string; type: ToastType; message: string }>>([]);

    const token = localStorage.getItem("access");

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [ownershipRes, customersRes, productsRes] = await Promise.all([
                api.get("/product-ownerships/"),
                api.get("/users/?role=customer"),
                api.get("/products/?page_size=1000"),
            ]);

            setOwnerships(Array.isArray(ownershipRes.data) ? ownershipRes.data : ownershipRes.data.results || []);
            setCustomers(Array.isArray(customersRes.data) ? customersRes.data : customersRes.data.results || []);
            setProducts(Array.isArray(productsRes.data) ? productsRes.data : productsRes.data.results || []);
        } catch (error) {
            showToast("error", "Veriler yüklenirken hata oluştu");
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
        if (!selectedCustomer || !selectedProduct || !purchaseDate) {
            showToast("error", "Lütfen tüm zorunlu alanları doldurun");
            return;
        }

        setSubmitting(true);
        try {
            await api.post("/product-ownerships/", {
                customer: selectedCustomer,
                product: selectedProduct,
                purchase_date: purchaseDate,
                serial_number: serialNumber || null,
            });

            showToast("success", "Ürün müşteriye başarıyla atandı");
            setModalOpen(false);
            resetForm();
            fetchData();
        } catch (error: any) {
            showToast("error", error.response?.data?.detail || error.message || "Bir hata oluştu");
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!window.confirm("Bu atamayı silmek istediğinizden emin misiniz?")) return;

        try {
            const res = await api.delete(`/product-ownerships/${id}/`);
            if (res.status === 204 || res.status === 200) {
                showToast("success", "Atama silindi");
                fetchData();
            }
        } catch (error: any) {
            showToast("error", error.message || "Silme işlemi başarısız");
        }
    };

    const resetForm = () => {
        setSelectedCustomer("");
        setSelectedProduct("");
        setPurchaseDate(new Date().toISOString().split("T")[0]);
        setSerialNumber("");
    };

    const filteredOwnerships = useMemo(() => {
        if (!searchTerm) return ownerships;
        const term = searchTerm.toLowerCase();
        return ownerships.filter(
            (o) =>
                o.customer?.username?.toLowerCase().includes(term) ||
                o.customer?.email?.toLowerCase().includes(term) ||
                o.product?.name?.toLowerCase().includes(term)
        );
    }, [ownerships, searchTerm]);

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString("tr-TR", {
            day: "numeric",
            month: "long",
            year: "numeric",
        });
    };

    const isWarrantyActive = (endDate?: string) => {
        if (!endDate) return false;
        return new Date(endDate) >= new Date();
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
                            <Package className="text-blue-600" />
                            <h1 className="text-2xl font-bold text-gray-900">Ürün Atamaları</h1>
                        </div>
                        <button
                            onClick={() => setModalOpen(true)}
                            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
                        >
                            <Plus />
                            Yeni Atama
                        </button>
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 overflow-y-auto p-6">
                    <div className="max-w-[1400px] mx-auto space-y-6">
                        {/* Stats */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="bg-white rounded-xl border border-gray-200 p-4">
                                <p className="text-sm text-gray-600 mb-1">Toplam Atama</p>
                                <p className="text-3xl font-bold text-gray-900">{ownerships.length}</p>
                            </div>
                            <div className="bg-white rounded-xl border border-gray-200 p-4">
                                <p className="text-sm text-gray-600 mb-1">Aktif Garantiler</p>
                                <p className="text-3xl font-bold text-green-600">
                                    {ownerships.filter((o) => isWarrantyActive(o.warranty_end_date)).length}
                                </p>
                            </div>
                            <div className="bg-white rounded-xl border border-gray-200 p-4">
                                <p className="text-sm text-gray-600 mb-1">Süresi Dolan Garantiler</p>
                                <p className="text-3xl font-bold text-red-600">
                                    {ownerships.filter((o) => !isWarrantyActive(o.warranty_end_date)).length}
                                </p>
                            </div>
                        </div>

                        {/* Search */}
                        <div className="bg-white rounded-xl border border-gray-200 p-4">
                            <div className="relative max-w-md">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="Müşteri veya ürün ara..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                            </div>
                        </div>

                        {/* Table */}
                        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                            <div className="px-4 py-3 border-b border-gray-200">
                                <span className="text-sm text-gray-600">{filteredOwnerships.length} kayıt</span>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-gray-50 border-b border-gray-200">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Müşteri</th>
                                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Ürün</th>
                                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Satın Alma</th>
                                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Garanti Durumu</th>
                                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">İşlemler</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200">
                                        {filteredOwnerships.length === 0 ? (
                                            <tr>
                                                <td colSpan={5} className="px-4 py-12 text-center text-gray-500">
                                                    <Users className="mx-auto mb-2" />
                                                    <p className="font-medium">Henüz atama yok</p>
                                                    <p className="text-sm mt-1">"Yeni Atama" ile başlayın</p>
                                                </td>
                                            </tr>
                                        ) : (
                                            filteredOwnerships.map((ownership) => (
                                                <tr key={ownership.id} className="hover:bg-gray-50">
                                                    <td className="px-4 py-3">
                                                        <div>
                                                            <p className="font-medium text-gray-900">
                                                                {ownership.customer?.first_name} {ownership.customer?.last_name}
                                                            </p>
                                                            <p className="text-sm text-gray-500">{ownership.customer?.email}</p>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <div>
                                                            <p className="font-medium text-gray-900">{ownership.product?.name}</p>
                                                            <p className="text-xs text-blue-600 font-mono">{ownership.product?.model_code}</p>
                                                            {ownership.serial_number && (
                                                                <p className="text-xs text-gray-400">SN: {ownership.serial_number}</p>
                                                            )}
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                        <div className="flex items-center gap-1">
                                                            <Calendar className="w-4 h-4" />
                                                            {formatDate(ownership.purchase_date)}
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        {isWarrantyActive(ownership.warranty_end_date) ? (
                                                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                                                                <CheckCircle className="w-3 h-3" />
                                                                Aktif ({formatDate(ownership.warranty_end_date!)})
                                                            </span>
                                                        ) : (
                                                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                                                                <AlertCircle className="w-3 h-3" />
                                                                Süresi Doldu
                                                            </span>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <button
                                                            onClick={() => handleDelete(ownership.id)}
                                                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                                            title="Sil"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </main>
            </div>

            {/* Modal */}
            {modalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl w-full max-w-lg mx-4 shadow-2xl">
                        <div className="flex items-center justify-between p-4 border-b border-gray-200">
                            <h2 className="text-lg font-bold text-gray-900">Yeni Ürün Ataması</h2>
                            <button onClick={() => setModalOpen(false)} className="p-1 hover:bg-gray-100 rounded">
                                <X />
                            </button>
                        </div>

                        <div className="p-4 space-y-4">
                            {/* Customer Select */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Müşteri <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={selectedCustomer}
                                    onChange={(e) => setSelectedCustomer(Number(e.target.value) || "")}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                >
                                    <option value="">Müşteri seçin...</option>
                                    {customers.map((c) => (
                                        <option key={c.id} value={c.id}>
                                            {c.first_name} {c.last_name} ({c.email})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Product Select */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Ürün <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={selectedProduct}
                                    onChange={(e) => setSelectedProduct(Number(e.target.value) || "")}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                >
                                    <option value="">Ürün seçin...</option>
                                    {products.map((p) => (
                                        <option key={p.id} value={p.id}>
                                            {p.name} ({p.model_code || p.brand})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Purchase Date */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Satın Alma Tarihi <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="date"
                                    value={purchaseDate}
                                    onChange={(e) => setPurchaseDate(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                            </div>

                            {/* Serial Number */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Seri Numarası (Opsiyonel)</label>
                                <input
                                    type="text"
                                    value={serialNumber}
                                    onChange={(e) => setSerialNumber(e.target.value)}
                                    placeholder="Örn: SN123456789"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
                            <button
                                onClick={() => setModalOpen(false)}
                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium"
                            >
                                İptal
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={submitting}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium flex items-center gap-2"
                            >
                                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                Ata
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
