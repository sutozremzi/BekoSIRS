import React from "react";
import { useNavigate } from "react-router-dom";

export default function NotFoundPage() {
    const navigate = useNavigate();

    return (
        <div style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
            fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
            background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
            color: "#e2e8f0",
            textAlign: "center",
            padding: "2rem",
        }}>
            <h1 style={{
                fontSize: "8rem",
                fontWeight: 800,
                margin: 0,
                background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                lineHeight: 1,
            }}>
                404
            </h1>
            <p style={{
                fontSize: "1.5rem",
                margin: "1rem 0 0.5rem",
                fontWeight: 600,
            }}>
                Sayfa Bulunamadı
            </p>
            <p style={{
                fontSize: "1rem",
                color: "#94a3b8",
                maxWidth: "400px",
                marginBottom: "2rem",
            }}>
                Aradığınız sayfa mevcut değil veya taşınmış olabilir.
            </p>
            <div style={{ display: "flex", gap: "1rem" }}>
                <button
                    onClick={() => navigate(-1)}
                    style={{
                        padding: "0.75rem 1.5rem",
                        borderRadius: "0.5rem",
                        border: "1px solid #475569",
                        background: "transparent",
                        color: "#e2e8f0",
                        cursor: "pointer",
                        fontSize: "0.95rem",
                        transition: "all 0.2s",
                    }}
                    onMouseOver={(e) => (e.currentTarget.style.background = "#1e293b")}
                    onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}
                >
                    ← Geri Dön
                </button>
                <button
                    onClick={() => navigate("/dashboard")}
                    style={{
                        padding: "0.75rem 1.5rem",
                        borderRadius: "0.5rem",
                        border: "none",
                        background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                        color: "#fff",
                        cursor: "pointer",
                        fontSize: "0.95rem",
                        fontWeight: 600,
                        transition: "all 0.2s",
                    }}
                    onMouseOver={(e) => (e.currentTarget.style.opacity = "0.9")}
                    onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
                >
                    Dashboard'a Git
                </button>
            </div>
        </div>
    );
}
