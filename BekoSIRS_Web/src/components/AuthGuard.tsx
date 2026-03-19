import React from "react";
import { Navigate } from "react-router-dom";

interface AuthGuardProps {
    children: React.ReactNode;
    allowedRoles?: string[];
}

/**
 * AuthGuard: Token yoksa kullanıcıyı login sayfasına yönlendirir.
 * Dashboard ve alt sayfalarını korur.
 */
export default function AuthGuard({ children, allowedRoles }: AuthGuardProps) {
    const token = localStorage.getItem("access");
    const userRole = localStorage.getItem("user_role");

    if (!token) {
        return <Navigate to="/" replace />;
    }

    if (allowedRoles && (!userRole || !allowedRoles.includes(userRole))) {
        return <Navigate to="/dashboard" replace />;
    }

    return <>{children}</>;
}
