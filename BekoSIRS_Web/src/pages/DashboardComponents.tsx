import React from "react";
import type { LucideIcon } from "lucide-react";

// --- KPI CARD ---
interface KpiCardProps {
    title: string;
    value: number | string;
    icon: LucideIcon;
    color: string;
    onClick?: () => void;
    subtext?: string;
    loading?: boolean;
}

export const KpiCard: React.FC<KpiCardProps> = ({ title, value, icon: Icon, color, onClick, subtext, loading }) => {
    return (
        <div
            onClick={onClick}
            className={`bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all cursor-pointer group relative overflow-hidden`}
        >
            <div className={`absolute right-0 top-0 w-24 h-24 bg-${color}-50 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110`} />

            <div className="relative flex justify-between items-start">
                <div>
                    <p className="text-gray-500 text-sm font-medium mb-1">{title}</p>
                    {loading ? (
                        <div className="h-8 w-16 bg-gray-200 animate-pulse rounded" />
                    ) : (
                        <h3 className="text-3xl font-bold text-gray-900">{value}</h3>
                    )}
                    {subtext && <p className="text-xs text-gray-400 mt-2">{subtext}</p>}
                </div>
                <div className={`p-3 bg-${color}-100 text-${color}-600 rounded-xl group-hover:bg-${color}-600 group-hover:text-white transition-colors`}>
                    <Icon size={24} />
                </div>
            </div>
        </div>
    );
};

// --- ALERT ITEM ---
interface AlertItemProps {
    title: string;
    message: string;
    severity: "critical" | "warning" | "info";
    onClick?: () => void;
}

export const AlertItem: React.FC<AlertItemProps> = ({ title, message, severity, onClick }) => {
    const colors = {
        critical: "bg-red-50 border-red-100 text-red-700",
        warning: "bg-yellow-50 border-yellow-100 text-yellow-700",
        info: "bg-blue-50 border-blue-100 text-blue-700",
    };

    return (
        <div
            onClick={onClick}
            className={`${colors[severity]} border p-4 rounded-xl flex items-start gap-3 cursor-pointer hover:opacity-80 transition-opacity`}
        >
            <div className={`w-2 h-2 mt-2 rounded-full ${severity === 'critical' ? 'bg-red-500' : severity === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'}`} />
            <div>
                <h4 className="font-semibold text-sm">{title}</h4>
                <p className="text-xs opacity-90 mt-0.5">{message}</p>
            </div>
        </div>
    );
};

// --- SIMPLE BAR CHART ---
interface ChartData {
    name: string;
    value: number;
}

export const SimpleBarChart: React.FC<{ data: ChartData[], title: string }> = ({ data, title }) => {
    const maxValue = Math.max(...data.map(d => d.value), 1); // Avoid div by zero

    return (
        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm h-full">
            <h3 className="font-bold text-gray-900 mb-6">{title}</h3>
            <div className="space-y-4">
                {data.map((item) => (
                    <div key={item.name}>
                        <div className="flex justify-between text-sm mb-1">
                            <span className="text-gray-600 font-medium">{item.name}</span>
                            <span className="font-bold text-gray-900">{item.value}</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                            <div
                                className="bg-blue-600 h-2.5 rounded-full transition-all duration-1000 ease-out"
                                style={{ width: `${(item.value / maxValue) * 100}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
