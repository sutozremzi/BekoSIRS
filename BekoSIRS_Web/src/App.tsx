import React, { lazy, Suspense } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

import AuthGuard from "./components/AuthGuard";

const LoginPage = lazy(() => import("./pages/LoginPage"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const ProductsPage = lazy(() => import("./pages/ProductsPage"));
const AddProductPage = lazy(() => import("./pages/AddProductPage"));
const CategoriesPage = lazy(() => import("./pages/CategoriesPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const CustomersPage = lazy(() => import("./pages/CustomersPage"));
const GroupsPage = lazy(() => import("./pages/GroupsPage"));
const ServiceRequestsPage = lazy(() => import("./pages/ServiceRequestsPage"));
const ReviewsPage = lazy(() => import("./pages/ReviewsPage"));
const AssignmentsPage = lazy(() => import("./pages/AssignmentsPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const DepotsPage = lazy(() => import("./pages/DepotsPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const InstallmentPlansPage = lazy(() => import("./pages/InstallmentPlansPage"));

const PageLoading = () => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-600">
    Yukleniyor...
  </div>
);

export default function App() {
  return (
    <Router>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/dashboard" element={<AuthGuard><Dashboard /></AuthGuard>} />
          <Route path="/dashboard/analytics" element={<AuthGuard><AnalyticsPage /></AuthGuard>} />
          <Route path="/dashboard/installments" element={<AuthGuard><InstallmentPlansPage /></AuthGuard>} />
          <Route path="/dashboard/products" element={<AuthGuard><ProductsPage /></AuthGuard>} />
          <Route path="/dashboard/products/add" element={<AuthGuard><AddProductPage /></AuthGuard>} />
          <Route path="/dashboard/categories" element={<AuthGuard><CategoriesPage /></AuthGuard>} />
          <Route path="/dashboard/users" element={<AuthGuard allowedRoles={["admin"]}><UsersPage /></AuthGuard>} />
          <Route path="/dashboard/customers" element={<AuthGuard><CustomersPage /></AuthGuard>} />
          <Route path="/dashboard/groups" element={<AuthGuard><GroupsPage /></AuthGuard>} />
          <Route path="/dashboard/service-requests" element={<AuthGuard><ServiceRequestsPage /></AuthGuard>} />
          <Route path="/dashboard/reviews" element={<AuthGuard><ReviewsPage /></AuthGuard>} />
          <Route path="/dashboard/assignments" element={<AuthGuard><AssignmentsPage /></AuthGuard>} />
          <Route path="/dashboard/notifications" element={<AuthGuard><NotificationsPage /></AuthGuard>} />
          <Route path="/dashboard/deliveries" element={<Navigate to="/dashboard/assignments" replace />} />
          <Route path="/dashboard/depots" element={<AuthGuard><DepotsPage /></AuthGuard>} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </Router>
  );
}
