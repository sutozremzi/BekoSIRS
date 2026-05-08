import React from "react";
import { useNavigate } from "react-router-dom";
import { Home, Bell, Settings, User } from "lucide-react";

export default function Navbar() {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate("/dashboard");
  };

  const handleLogout = () => {
    if (window.confirm("Çıkış yapmak istediğinizden emin misiniz?")) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      navigate("/");
    }
  };

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Left - Logo */}
          <div className="flex items-center space-x-4">
            <div className="bg-black text-white px-4 py-2 rounded-lg font-bold text-xl">
              BEKO
            </div>
            <div className="hidden md:block">
              <span className="text-gray-600 text-sm font-medium">Yönetim Paneli</span>
            </div>
          </div>

          {/* Center - Navigation Links (Optional) */}
          <div className="hidden lg:flex items-center space-x-1">
            <button
              onClick={handleGoHome}
              className="px-4 py-2 text-gray-700 hover:text-black hover:bg-gray-100 rounded-lg transition-all font-medium flex items-center space-x-2"
            >
              <Home size={18} />
              <span>Ana Sayfa</span>
            </button>
          </div>

          {/* Right - Actions */}
          <div className="flex items-center space-x-3">

            {/* Notifications */}
            <button className="p-2 text-gray-600 hover:text-black hover:bg-gray-100 rounded-full transition-all relative">
              <Bell size={20} />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>

            {/* Settings */}
            <button className="p-2 text-gray-600 hover:text-black hover:bg-gray-100 rounded-full transition-all">
              <Settings size={20} />
            </button>

            {/* User Menu */}
            <div className="flex items-center space-x-3 pl-3 border-l border-gray-200">
              <div className="hidden md:flex items-center space-x-3">
                <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                  <User size={18} className="text-white" />
                </div>
                <div className="hidden lg:block">
                  <p className="text-sm font-semibold text-gray-900">Admin</p>
                  <p className="text-xs text-gray-500">Yönetici</p>
                </div>
              </div>

              <button
                onClick={handleLogout}
                className="bg-black text-white px-5 py-2 rounded-full hover:bg-gray-800 transition-all font-medium text-sm"
              >
                Çıkış
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}