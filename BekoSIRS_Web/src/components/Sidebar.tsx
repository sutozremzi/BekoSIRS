import React, { useState } from "react";
import { Package, Tag, Users, Layers, LogOut, Menu, X, Home, Wrench, Star, BoxSelect, Bell, Truck, CreditCard, BarChart3 } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

export default function Sidebar() {
  const [open, setOpen] = useState(true);
  const location = useLocation();

  const menus = [
    { name: "Dashboard", icon: <Home size={20} />, link: "/dashboard" },
    { name: "Analitikler", icon: <BarChart3 size={20} />, link: "/dashboard/analytics" },
    { name: "Ürünler", icon: <Package size={20} />, link: "/dashboard/products" },
    { name: "Kategoriler", icon: <Tag size={20} />, link: "/dashboard/categories" },
    { name: "Servis Talepleri", icon: <Wrench size={20} />, link: "/dashboard/service-requests" },
    { name: "Değerlendirmeler", icon: <Star size={20} />, link: "/dashboard/reviews" },
    { name: "Gruplar", icon: <Layers size={20} />, link: "/dashboard/groups" },
    { name: "Kullanıcılar", icon: <Users size={20} />, link: "/dashboard/users" },
    { name: "Ürün Atamaları", icon: <BoxSelect size={20} />, link: "/dashboard/assignments" },
    { name: "Taksit Yönetimi", icon: <CreditCard size={20} />, link: "/dashboard/installments" },
    { name: "Teslimatlar", icon: <Truck size={20} />, link: "/dashboard/deliveries" },
    { name: "Bildirimler", icon: <Bell size={20} />, link: "/dashboard/notifications" },
  ];

  const handleLogout = () => {
    if (window.confirm("Çıkış yapmak istediğinizden emin misiniz?")) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      window.location.href = "/";
    }
  };

  const isActive = (link: string) => {
    return location.pathname === link;
  };

  return (
    <div
      className={`${open ? "w-64" : "w-20"
        } bg-white border-r border-gray-200 min-h-screen duration-300 flex flex-col shadow-sm`}
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className={`flex items-center space-x-3 ${!open && "justify-center w-full"}`}>
            <div className="bg-black text-white px-3 py-2 rounded-lg font-bold text-lg">
              BEKO
            </div>
            {open && (
              <div>
                <p className="text-sm font-semibold text-gray-900">Admin Panel</p>
                <p className="text-xs text-gray-500">Yönetim Sistemi</p>
              </div>
            )}
          </div>
          {open && (
            <button
              onClick={() => setOpen(false)}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X size={20} className="text-gray-600" />
            </button>
          )}
        </div>

        {!open && (
          <button
            onClick={() => setOpen(true)}
            className="mt-4 p-2 hover:bg-gray-100 rounded-lg transition-colors w-full flex justify-center"
          >
            <Menu size={20} className="text-gray-600" />
          </button>
        )}
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 p-4 space-y-1">
        {menus.map((menu, index) => {
          const active = isActive(menu.link);
          return (
            <Link
              to={menu.link}
              key={index}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${active
                ? "bg-black text-white shadow-lg"
                : "text-gray-700 hover:bg-gray-100"
                }`}
            >
              <span className={active ? "text-white" : "text-gray-600 group-hover:text-black"}>
                {menu.icon}
              </span>
              <span
                className={`text-sm font-medium duration-200 ${!open && "hidden"
                  }`}
              >
                {menu.name}
              </span>
              {active && open && (
                <span className="ml-auto w-1.5 h-1.5 bg-white rounded-full"></span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Profile Section */}
      {open && (
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center space-x-3 px-3 py-3 bg-gray-50 rounded-xl">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
              <span className="text-white font-bold text-sm">A</span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-900">Admin</p>
              <p className="text-xs text-gray-500">Yönetici</p>
            </div>
          </div>
        </div>
      )}

      {/* Logout Button */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={handleLogout}
          className={`flex items-center gap-3 w-full px-4 py-3 text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200 group ${!open && "justify-center"
            }`}
        >
          <LogOut size={20} />
          {open && <span className="text-sm font-medium">Çıkış Yap</span>}
        </button>
      </div>
    </div>
  );
}