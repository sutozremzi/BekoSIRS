import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

import AuthGuard from "./components/AuthGuard";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import ProductsPage from "./pages/ProductsPage";
import AddProductPage from "./pages/AddProductPage";
import CategoriesPage from "./pages/CategoriesPage";
import UsersPage from "./pages/UsersPage";
import CustomersPage from "./pages/CustomersPage";
import GroupsPage from "./pages/GroupsPage";
import ServiceRequestsPage from "./pages/ServiceRequestsPage";
import ReviewsPage from "./pages/ReviewsPage";
import AssignmentsPage from "./pages/AssignmentsPage";
import NotificationsPage from "./pages/NotificationsPage";
import DeliveriesPage from "./pages/DeliveriesPage";
import DepotsPage from "./pages/DepotsPage";
import NotFoundPage from "./pages/NotFoundPage";

import AnalyticsPage from "./pages/AnalyticsPage";
import InstallmentPlansPage from "./pages/InstallmentPlansPage";

export default function App() {
  return (
    <Router>
      <Routes>
        {/* 🔹 Giriş sayfası (herkese açık) */}
        <Route path="/" element={<LoginPage />} />

        {/* 🔹 Korumalı sayfalar — token yoksa login'e yönlendirir */}
        <Route path="/dashboard" element={<AuthGuard><Dashboard /></AuthGuard>} />
        <Route path="/dashboard/analytics" element={<AuthGuard><AnalyticsPage /></AuthGuard>} />
        <Route path="/dashboard/installments" element={<AuthGuard><InstallmentPlansPage /></AuthGuard>} />
        <Route path="/dashboard/products" element={<AuthGuard><ProductsPage /></AuthGuard>} />
        <Route path="/dashboard/products/add" element={<AuthGuard><AddProductPage /></AuthGuard>} />
        <Route path="/dashboard/categories" element={<AuthGuard><CategoriesPage /></AuthGuard>} />
        <Route path="/dashboard/users" element={<AuthGuard><UsersPage /></AuthGuard>} />
        <Route path="/dashboard/customers" element={<AuthGuard><CustomersPage /></AuthGuard>} />
        <Route path="/dashboard/groups" element={<AuthGuard><GroupsPage /></AuthGuard>} />
        <Route path="/dashboard/service-requests" element={<AuthGuard><ServiceRequestsPage /></AuthGuard>} />
        <Route path="/dashboard/reviews" element={<AuthGuard><ReviewsPage /></AuthGuard>} />
        <Route path="/dashboard/assignments" element={<AuthGuard><AssignmentsPage /></AuthGuard>} />
        <Route path="/dashboard/notifications" element={<AuthGuard><NotificationsPage /></AuthGuard>} />
        <Route path="/dashboard/deliveries" element={<AuthGuard><DeliveriesPage /></AuthGuard>} />
        <Route path="/dashboard/depots" element={<AuthGuard><DepotsPage /></AuthGuard>} />

        {/* 🔹 404 sayfası */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Router>
  );
}
