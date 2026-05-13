import React, { useState } from "react";
import {
  Package,
  Tag,
  Users,
  Layers,
  LogOut,
  Menu,
  X,
  Home,
  Wrench,
  Star,
  BoxSelect,
  Bell,
  UserCheck,
  MapPin,
  BarChart3,
  CreditCard,
  Globe,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

type MenuItem = {
  name: string;
  icon: React.ReactNode;
  link: string;
  adminOnly?: boolean;
};

export default function Sidebar() {
  const [open, setOpen] = useState(true);
  const location = useLocation();
  const userRole = (localStorage.getItem("user_role") || "").toLowerCase();
  const isAdmin = userRole === "admin";
  const { t, i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'tr' ? 'en' : 'tr';
    i18n.changeLanguage(newLang);
  };

  const menus: MenuItem[] = [
    { name: t('sidebar.dashboard'), icon: <Home size={20} />, link: "/dashboard" },
    { name: t('sidebar.analytics'), icon: <BarChart3 size={20} />, link: "/dashboard/analytics" },
    { name: t('sidebar.installments'), icon: <CreditCard size={20} />, link: "/dashboard/installments" },
    { name: t('sidebar.products'), icon: <Package size={20} />, link: "/dashboard/products" },
    { name: t('sidebar.categories'), icon: <Tag size={20} />, link: "/dashboard/categories" },
    { name: t('sidebar.serviceRequests'), icon: <Wrench size={20} />, link: "/dashboard/service-requests" },
    { name: t('sidebar.reviews'), icon: <Star size={20} />, link: "/dashboard/reviews" },
    { name: t('sidebar.groups'), icon: <Layers size={20} />, link: "/dashboard/groups" },
    { name: t('sidebar.users'), icon: <Users size={20} />, link: "/dashboard/users", adminOnly: true },
    { name: t('sidebar.customers'), icon: <UserCheck size={20} />, link: "/dashboard/customers" },
    { name: t('sidebar.assignments'), icon: <BoxSelect size={20} />, link: "/dashboard/assignments" },
    { name: t('sidebar.depots'), icon: <MapPin size={20} />, link: "/dashboard/depots" },
    { name: t('sidebar.notifications'), icon: <Bell size={20} />, link: "/dashboard/notifications" },
  ];

  const visibleMenus = menus.filter((menu) => !menu.adminOnly || isAdmin);

  const handleLogout = () => {
    if (window.confirm(t('sidebar.logoutConfirm'))) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      localStorage.removeItem("user_role");
      window.location.href = "/";
    }
  };

  const isActive = (link: string) => location.pathname === link;

  return (
    <div
      className={`${
        open ? "w-64" : "w-20"
      } bg-white border-r border-gray-200 min-h-screen duration-300 flex flex-col shadow-sm`}
    >
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className={`flex items-center space-x-3 ${!open && "justify-center w-full"}`}>
            <div className="bg-black text-white px-3 py-2 rounded-lg font-bold text-lg">BEKO SIRS</div>
            {open && (
              <div>
                <p className="text-sm font-semibold text-gray-900">{t('sidebar.adminPanel')}</p>
                <p className="text-xs text-gray-500">{isAdmin ? t('sidebar.manager') : t('sidebar.sellerPanel')}</p>
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

      <nav className="flex-1 p-4 space-y-1">
        {visibleMenus.map((menu, index) => {
          const active = isActive(menu.link);
          return (
            <Link
              to={menu.link}
              key={index}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                active ? "bg-black text-white shadow-lg" : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <span className={active ? "text-white" : "text-gray-600 group-hover:text-black"}>
                {menu.icon}
              </span>
              <span className={`text-sm font-medium duration-200 ${!open && "hidden"}`}>
                {menu.name}
              </span>
              {active && open && <span className="ml-auto w-1.5 h-1.5 bg-white rounded-full"></span>}
            </Link>
          );
        })}
      </nav>

      {open && (
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center space-x-3 px-3 py-3 bg-gray-50 rounded-xl">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
              <span className="text-white font-bold text-sm">{isAdmin ? t('sidebar.admin')[0] : t('sidebar.seller')[0]}</span>
            </div>
            <div className="flex-1 flex flex-col items-start justify-center">
              <button
                onClick={toggleLanguage}
                className="flex items-center space-x-1 text-[10px] text-gray-500 hover:text-black bg-gray-200 px-1.5 py-0.5 rounded mb-1 w-max transition-colors"
                title={t('navbar.language')}
              >
                <Globe size={10} />
                <span className="font-bold uppercase">{i18n.language}</span>
              </button>
              <p className="text-sm font-semibold text-gray-900 leading-tight">{isAdmin ? t('sidebar.admin') : t('sidebar.seller')}</p>
              <p className="text-xs text-gray-500 leading-tight">{isAdmin ? t('sidebar.manager') : t('sidebar.authUser')}</p>
            </div>
          </div>
        </div>
      )}

      <div className="p-4 border-t border-gray-200">
        <button
          onClick={handleLogout}
          className={`flex items-center gap-3 w-full px-4 py-3 text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200 group ${
            !open && "justify-center"
          }`}
        >
          <LogOut size={20} />
          {open && <span className="text-sm font-medium">{t('sidebar.logout')}</span>}
        </button>
      </div>
    </div>
  );
}
