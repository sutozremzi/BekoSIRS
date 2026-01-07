// src/pages/DeliveriesPage.tsx
import React, { useEffect, useState } from "react";
import * as Lucide from "lucide-react";
import Sidebar from "../components/Sidebar";
import { ToastContainer, type ToastType } from "../components/Toast";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import api from "../services/api";

// Fix Leaflet Default Icon
import iconMarker2x from 'leaflet/dist/images/marker-icon-2x.png';
import iconMarker from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: iconMarker2x,
    iconUrl: iconMarker,
    shadowUrl: iconShadow,
});

// Custom Icons
const storeIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-black.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

const deliveryIcon = (color: string) => new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

const {
    Truck = () => <span>🚚</span>,
    MapPin = () => <span>📍</span>,
    Calendar = () => <span>📅</span>,
    Plus = () => <span>+</span>,
    Route = () => <span>🛤️</span>,
    Loader2 = () => <span>↻</span>,
    X = () => <span>✕</span>,
    CheckCircle = () => <span>✓</span>,
    Clock = () => <span>🕐</span>,
    Navigation = () => <span>🧭</span>,
    Target = () => <span>🎯</span>,
} = Lucide as any;

interface Customer {
    id: number;
    username: string;
    full_name: string;
    first_name: string;
    last_name: string;
    phone?: string;
    address?: string;
    address_city?: string;
    address_lat?: string;
    address_lng?: string;
}

interface Delivery {
    id: number;
    customer: Customer;
    product?: string;
    delivery_date: string;
    status: string;
    status_display: string;
    address: string;
    address_lat?: number;
    address_lng?: number;
    notes: string;
}

interface RouteStop {
    order: number;
    delivery_id: number;
    customer: string;
    address: string;
    lat?: number;
    lng?: number;
    distance_km?: number;
    duration_min?: number;
}

interface OptimizedRoute {
    route_id: number;
    stop_count: number;
    total_distance_km: number;
    total_duration_min: number;
    stops: RouteStop[];
    store?: { lat: number; lng: number; address: string };
}

const statusColors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    assigned: "bg-blue-100 text-blue-700",
    in_transit: "bg-purple-100 text-purple-700",
    delivered: "bg-green-100 text-green-700",
    cancelled: "bg-red-100 text-red-700",
};

// Map click handler component
function LocationPicker({ onLocationSelect }: { onLocationSelect: (lat: number, lng: number) => void }) {
    useMapEvents({
        click(e) {
            onLocationSelect(e.latlng.lat, e.latlng.lng);
        },
    });
    return null;
}

// Map bounds updater
function MapBoundsUpdater({ bounds }: { bounds: L.LatLngBoundsExpression | null }) {
    const map = useMap();
    useEffect(() => {
        if (bounds) {
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }, [bounds, map]);
    return null;
}

export default function DeliveriesPage() {
    const [deliveries, setDeliveries] = useState<Delivery[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
    const [optimizedRoute, setOptimizedRoute] = useState<OptimizedRoute | null>(null);
    const [optimizing, setOptimizing] = useState(false);
    const [showAddModal, setShowAddModal] = useState(false);
    const [customers, setCustomers] = useState<Customer[]>([]);
    const [toasts, setToasts] = useState<Array<{ id: string; type: ToastType; message: string }>>([]);

    // Form state
    const [formCustomerId, setFormCustomerId] = useState("");
    const [formAddress, setFormAddress] = useState("");
    const [formNotes, setFormNotes] = useState("");
    const [formLat, setFormLat] = useState<string>("");
    const [formLng, setFormLng] = useState<string>("");
    const [submitting, setSubmitting] = useState(false);
    const [pickingLocation, setPickingLocation] = useState(false);

    const token = localStorage.getItem("access");

    // Lefkoşa Center Default
    const DEFAULT_CENTER: [number, number] = [35.1856, 33.3823];

    useEffect(() => {
        fetchDeliveries();
        fetchCustomers();
        fetchRoute();
    }, [selectedDate]);

    const fetchDeliveries = async () => {
        setLoading(true);
        try {
            const res = await api.get(`/deliveries/?date=${selectedDate}`);
            setDeliveries(res.data);
        } catch (error) {
            console.error("Fetch error:", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchRoute = async () => {
        try {
            const res = await api.get(`/delivery-routes/by-date/${selectedDate}/`);
            setOptimizedRoute(res.data);
        } catch (error) {
            // 404 is expected if no route exists
            setOptimizedRoute(null);
        }
    };

    const fetchCustomers = async () => {
        try {
            const res = await api.get("/users/?role=customer");
            setCustomers(Array.isArray(res.data) ? res.data : res.data.results || []);
        } catch (error) {
            console.error("Customers fetch error:", error);
        }
    };

    const handleOptimizeRoute = async () => {
        setOptimizing(true);
        try {
            const res = await api.post("/delivery-routes/optimize/", {
                date: selectedDate,
            });

            setOptimizedRoute(res.data);
            showToast("success", `Rota optimize edildi: ${res.data.total_distance_km} km`);
            fetchDeliveries();
        } catch (error: any) {
            const errData = error.response?.data;
            showToast("error", errData?.error || "Optimizasyon başarısız");
            if (errData?.missing) {
                showToast("warning", "Bazı teslimatların koordinatları eksik");
            }
        } finally {
            setOptimizing(false);
        }
    };

    const handleAddDelivery = async () => {
        if (!formCustomerId || !formAddress) {
            showToast("error", "Müşteri ve adres zorunludur");
            return;
        }

        setSubmitting(true);
        try {
            await api.post("/deliveries/", {
                customer_id: parseInt(formCustomerId),
                delivery_date: selectedDate,
                address: formAddress,
                address_lat: formLat ? parseFloat(formLat) : null,
                address_lng: formLng ? parseFloat(formLng) : null,
                notes: formNotes,
            });

            showToast("success", "Teslimat eklendi");
            setShowAddModal(false);
            resetForm();
            fetchDeliveries();
        } catch (error: any) {
            const errData = error.response?.data;
            showToast("error", errData?.error || "Eklenemedi");
        } finally {
            setSubmitting(false);
        }
    };

    const resetForm = () => {
        setFormCustomerId("");
        setFormAddress("");
        setFormNotes("");
        setFormLat("");
        setFormLng("");
        setPickingLocation(false);
    };

    const showToast = (type: ToastType, message: string) => {
        const id = Date.now().toString();
        setToasts((prev) => [...prev, { id, type, message }]);
    };

    const removeToast = (id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    // Helper to get route coordinates for Polyline
    const getRouteCoordinates = () => {
        if (!optimizedRoute) return [];

        // Default store location if not provided
        const storeLat = optimizedRoute.store?.lat || 35.1856;
        const storeLng = optimizedRoute.store?.lng || 33.3823;

        const coords: [number, number][] = [];

        // Start at store
        coords.push([storeLat, storeLng]);

        // Add all stops
        optimizedRoute.stops.forEach(stop => {
            if (stop.lat && stop.lng) {
                coords.push([stop.lat, stop.lng]);
            }
        });

        return coords;
    };

    // Calculate map bounds
    const getMapBounds = (): L.LatLngBoundsExpression | null => {
        const coords: [number, number][] = [];

        // Add delivery locations
        deliveries.forEach(d => {
            if (d.address_lat && d.address_lng) {
                coords.push([d.address_lat, d.address_lng]);
            }
        });

        // Add store location if routed
        if (optimizedRoute) {
            const storeLat = optimizedRoute.store?.lat || 35.1856;
            const storeLng = optimizedRoute.store?.lng || 33.3823;
            coords.push([storeLat, storeLng]);
        }

        if (coords.length === 0) return null;
        return coords;
    };

    return (
        <div className="flex min-h-screen bg-gray-50">
            <Sidebar />
            <ToastContainer toasts={toasts} onRemove={removeToast} />

            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Header */}
                <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
                    <div className="px-6 py-4 flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div className="p-2 bg-orange-100 rounded-lg">
                                <Truck className="w-5 h-5 text-orange-600" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-gray-900">Teslimat Yönetimi</h1>
                                <p className="text-sm text-gray-500">Teslimatları planla, haritada gör ve rotayı optimize et</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2">
                                <Calendar className="w-4 h-4 text-gray-600" />
                                <input
                                    type="date"
                                    value={selectedDate}
                                    onChange={(e) => setSelectedDate(e.target.value)}
                                    className="bg-transparent border-none outline-none text-sm font-medium"
                                />
                            </div>
                            <button
                                onClick={() => setShowAddModal(true)}
                                className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
                            >
                                <Plus className="w-4 h-4" />
                                Teslimat Ekle
                            </button>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">

                    {/* Left Panel: List */}
                    <div className="w-full lg:w-1/3 bg-white border-r border-gray-200 flex flex-col z-20 overflow-y-auto min-w-[350px]">
                        <div className="p-4 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white">
                            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                                <MapPin className="w-4 h-4" />
                                Teslimat Listesi ({deliveries.length})
                            </h2>
                            <button
                                onClick={handleOptimizeRoute}
                                disabled={optimizing || deliveries.length < 2}
                                className="flex items-center gap-2 px-3 py-1.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 text-sm font-medium transition-colors"
                            >
                                {optimizing ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Route className="w-4 h-4" />
                                )}
                                Optimize Et
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-3">
                            {deliveries.length === 0 ? (
                                <div className="text-center py-10 text-gray-500">
                                    <Truck className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p>Bu tarihte teslimat yok</p>
                                </div>
                            ) : (
                                deliveries.map((delivery, index) => (
                                    <div key={delivery.id} className="p-3 border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors group">
                                        <div className="flex items-start gap-3">
                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${delivery.status === 'assigned' ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
                                                }`}>
                                                {index + 1}
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex justify-between items-start">
                                                    <h3 className="font-medium text-gray-900">{delivery.customer.full_name}</h3>
                                                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${statusColors[delivery.status]}`}>
                                                        {delivery.status_display}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-600 mt-1">{delivery.address}</p>
                                                <div className="flex items-center gap-2 mt-2">
                                                    {delivery.address_lat ? (
                                                        <span className="text-xs text-green-600 flex items-center gap-1">
                                                            <CheckCircle className="w-3 h-3" /> Konum Var
                                                        </span>
                                                    ) : (
                                                        <span className="text-xs text-red-500 flex items-center gap-1">
                                                            <X className="w-3 h-3" /> Konum Yok
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        {/* Optimized Route Summary */}
                        {optimizedRoute && (
                            <div className="p-4 bg-gray-50 border-t border-gray-200">
                                <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                    <Navigation className="w-4 h-4" /> Rota Özeti
                                </h3>
                                <div className="grid grid-cols-3 gap-2 text-center">
                                    <div className="bg-white p-2 rounded border border-gray-200">
                                        <p className="text-lg font-bold text-orange-600">{optimizedRoute.stop_count}</p>
                                        <p className="text-xs text-gray-500">Durak</p>
                                    </div>
                                    <div className="bg-white p-2 rounded border border-gray-200">
                                        <p className="text-lg font-bold text-blue-600">{optimizedRoute.total_distance_km}</p>
                                        <p className="text-xs text-gray-500">Km</p>
                                    </div>
                                    <div className="bg-white p-2 rounded border border-gray-200">
                                        <p className="text-lg font-bold text-green-600">{optimizedRoute.total_duration_min} dk</p>
                                        <p className="text-xs text-gray-500">Tahmini</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right Panel: Map */}
                    <div className="flex-1 bg-gray-100 relative h-[50vh] lg:h-auto z-10">
                        <MapContainer center={DEFAULT_CENTER} zoom={11} className="w-full h-full">
                            <TileLayer
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            />

                            {/* Store Marker */}
                            <Marker position={[35.1856, 33.3823]} icon={storeIcon}>
                                <Popup>
                                    <strong>📍 Beko Mağaza</strong><br />
                                    Lefkoşa
                                </Popup>
                            </Marker>

                            {/* Delivery Markers */}
                            {deliveries.map((delivery) => (
                                delivery.address_lat && delivery.address_lng && (
                                    <Marker
                                        key={delivery.id}
                                        position={[delivery.address_lat, delivery.address_lng]}
                                        icon={deliveryIcon(delivery.status === 'assigned' ? 'blue' : 'gold')}
                                    >
                                        <Popup>
                                            <strong>📦 {delivery.customer.full_name}</strong><br />
                                            {delivery.address}<br />
                                            <span className="text-xs text-gray-500">{delivery.status_display}</span>
                                        </Popup>
                                    </Marker>
                                )
                            ))}

                            {/* Route Line */}
                            {optimizedRoute && (
                                <Polyline
                                    positions={getRouteCoordinates()}
                                    color="blue"
                                    weight={4}
                                    opacity={0.7}
                                    dashArray="10, 10"
                                />
                            )}

                            {/* Map Bounds Logic */}
                            <MapBoundsUpdater bounds={getMapBounds() || [DEFAULT_CENTER]} />
                        </MapContainer>
                    </div>

                </main>
            </div>

            {/* Add Delivery Modal with Map Picker */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl w-full max-w-4xl h-[90vh] shadow-2xl flex flex-col">
                        <div className="flex items-center justify-between p-4 border-b border-gray-200">
                            <h2 className="text-lg font-bold text-gray-900">Yeni Teslimat Ekle</h2>
                            <button onClick={() => setShowAddModal(false)} className="p-1 hover:bg-gray-100 rounded">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
                            {/* Form Side */}
                            <div className="w-full lg:w-1/3 p-4 overflow-y-auto border-r border-gray-200 space-y-4">
                                {/* Customer Select */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Müşteri <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        value={formCustomerId}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            setFormCustomerId(val);
                                            if (val) {
                                                const customer = customers.find(c => c.id === parseInt(val));
                                                if (customer) {
                                                    if (customer.address) setFormAddress(customer.address);
                                                    if (customer.address_lat) setFormLat(String(customer.address_lat));
                                                    if (customer.address_lng) setFormLng(String(customer.address_lng));
                                                }
                                            }
                                        }}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none"
                                    >
                                        <option value="">Müşteri seçin...</option>
                                        {customers.map((c) => (
                                            <option key={c.id} value={c.id}>
                                                {c.username}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* Address */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Teslimat Adresi <span className="text-red-500">*</span>
                                    </label>
                                    <textarea
                                        value={formAddress}
                                        onChange={(e) => setFormAddress(e.target.value)}
                                        placeholder="Örn: Girne Cad. No:45, Lefkoşa"
                                        rows={3}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none resize-none"
                                    />
                                </div>

                                {/* Coordinates Info */}
                                <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                                    <p className="text-xs font-semibold text-blue-800 mb-1 flex items-center gap-1">
                                        <Target className="w-3 h-3" /> Konum Seçimi
                                    </p>
                                    <p className="text-xs text-blue-600 mb-2">
                                        {pickingLocation ? "Haritadan bir noktaya tıklayın..." : "Sağdaki haritadan konumu işaretleyebilirsiniz."}
                                    </p>

                                    <div className="grid grid-cols-2 gap-2">
                                        <input
                                            type="text"
                                            value={formLat}
                                            readOnly
                                            placeholder="Enlem"
                                            className="bg-white px-2 py-1 text-xs border rounded text-gray-500"
                                        />
                                        <input
                                            type="text"
                                            value={formLng}
                                            readOnly
                                            placeholder="Boylam"
                                            className="bg-white px-2 py-1 text-xs border rounded text-gray-500"
                                        />
                                    </div>

                                    {!pickingLocation && !formLat && (
                                        <button
                                            onClick={() => setPickingLocation(true)}
                                            className="mt-2 w-full py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                                        >
                                            Konum Seçmek İçin Haritayı Kullan
                                        </button>
                                    )}

                                    {formLat && (
                                        <button
                                            onClick={() => {
                                                setFormLat("");
                                                setFormLng("");
                                                setPickingLocation(true);
                                            }}
                                            className="mt-2 w-full py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300"
                                        >
                                            Konumu Değiştir
                                        </button>
                                    )}
                                </div>

                                {/* Notes */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Notlar</label>
                                    <input
                                        type="text"
                                        value={formNotes}
                                        onChange={(e) => setFormNotes(e.target.value)}
                                        placeholder="Ek bilgiler..."
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none"
                                    />
                                </div>
                            </div>

                            {/* Map Picker Side */}
                            <div className="flex-1 bg-gray-100 relative">
                                <MapContainer center={DEFAULT_CENTER} zoom={11} className="w-full h-full">
                                    <TileLayer
                                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                    />
                                    <LocationPicker onLocationSelect={(lat, lng) => {
                                        setFormLat(lat.toFixed(6));
                                        setFormLng(lng.toFixed(6));
                                        setPickingLocation(false);
                                    }} />
                                    {formLat && formLng && (
                                        <Marker position={[parseFloat(formLat), parseFloat(formLng)]} icon={deliveryIcon('red')} />
                                    )}
                                </MapContainer>

                                {pickingLocation && (
                                    <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-black/80 text-white px-4 py-2 rounded-full text-sm font-bold z-[1000] shadow-lg animate-pulse pointer-events-none">
                                        📍 Lütfen haritadan teslimat noktasını seçin
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 p-4 border-t border-gray-200 bg-white">
                            <button
                                onClick={() => setShowAddModal(false)}
                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium"
                            >
                                İptal
                            </button>
                            <button
                                onClick={handleAddDelivery}
                                disabled={submitting}
                                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 text-sm font-medium flex items-center gap-2"
                            >
                                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                <CheckCircle className="w-4 h-4" />
                                Kaydet
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
