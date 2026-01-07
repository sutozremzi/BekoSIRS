import React, { useState, useEffect } from "react";
import Dashboard from "./Dashboard";
import { Lock, User, Eye, EyeOff, LogIn, AlertCircle } from "lucide-react";
import api from "../services/api";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Sayfa yüklendiğinde eski oturum verilerini temizleyerek "Tester" sızıntısını önle
  useEffect(() => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("user_role");
  }, []);

  const handleLogin = async () => {
    setLoading(true);
    setError("");

    try {
      // 127.0.0.1 yerine bazen localhost veya ağ IP'si gerekebilir, backend ile uyumlu tutun
      const response = await api.post("/token/", {
        username,
        password,
        platform: "web"
      });

      const data = response.data;

      // Başarılı giriş: Verileri sakla
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("user_role", data.role);

      setIsLoggedIn(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleLogin();
    }
  };

  if (isLoggedIn) {
    return <Dashboard />;
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sol Taraf - Görsel Alan */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-gray-900 via-gray-800 to-black relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-72 h-72 bg-white rounded-full blur-3xl"></div>
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-blue-500 rounded-full blur-3xl"></div>
        </div>

        <div className="relative z-10 flex flex-col justify-center px-16 text-white">
          <div className="mb-8">
            <div className="bg-white text-black px-6 py-3 rounded-2xl font-bold text-3xl inline-block mb-8">
              BEKO
            </div>
          </div>

          <h1 className="text-5xl font-bold mb-6 leading-tight">
            Ürün Yönetim<br />Sistemi
          </h1>

          <p className="text-xl text-gray-300 mb-12 leading-relaxed">
            Modern ve güçlü admin paneline hoş geldiniz.<br />
            Tüm ürünlerinizi tek bir yerden yönetin.
          </p>

          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
              <span className="text-gray-300">Kolay ürün yönetimi</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
              <span className="text-gray-300">Gerçek zamanlı güncelleme</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
              <span className="text-gray-300">Güvenli ve hızlı</span>
            </div>
          </div>
        </div>
      </div>

      {/* Sağ Taraf - Form Alanı */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-3xl shadow-xl border border-gray-200 p-8">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-black rounded-2xl mb-4">
                <Lock size={32} className="text-white" />
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                Yönetici Girişi
              </h2>
              <p className="text-gray-600">
                Lütfen kimlik bilgilerinizi doğrulayın
              </p>
            </div>

            {/* Dinamik Hata Paneli */}
            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3">
                <AlertCircle size={20} className="text-red-500 mt-0.5 flex-shrink-0" />
                <p className="text-red-600 text-sm font-medium">
                  {error}
                </p>
              </div>
            )}

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Kullanıcı Adı
                </label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-black transition-all"
                    placeholder="Kullanıcı adınız"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Şifre
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="w-full pl-12 pr-12 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-black transition-all"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>

              <button
                onClick={handleLogin}
                disabled={loading || !username || !password}
                className="w-full bg-black text-white py-3 rounded-xl hover:bg-gray-800 transition-all font-semibold flex items-center justify-center space-x-2 shadow-lg disabled:opacity-50"
              >
                {loading ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                ) : (
                  <>
                    <LogIn size={20} />
                    <span>Sisteme Giriş Yap</span>
                  </>
                )}
              </button>
            </div>
          </div>
          <p className="text-center text-sm text-gray-500 mt-8">
            © 2025 Beko Kurumsal.
          </p>
        </div>
      </div>
    </div>
  );
}