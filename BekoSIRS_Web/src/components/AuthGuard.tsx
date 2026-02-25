import React from "react";
import { Navigate } from "react-router-dom";

interface AuthGuardProps {
    children: React.ReactNode;
}

/**
 * AuthGuard: Token yoksa kullanıcıyı login sayfasına yönlendirir.
 * Dashboard ve alt sayfalarını korur.
 */
export default function AuthGuard({ children }: AuthGuardProps) {
    const token = localStorage.getItem("access");

    if (!token) {
        return <Navigate to="/" replace />;
    }

    return <>{children}</>;
}
