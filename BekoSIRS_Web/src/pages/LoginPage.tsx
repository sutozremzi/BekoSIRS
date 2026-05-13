import React, { useState, useEffect, useRef } from "react";
import Dashboard from "./Dashboard";
import {
  Lock,
  User,
  Eye,
  EyeOff,
  LogIn,
  AlertCircle,
  Package,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import api from "../services/api";
import { useTranslation } from "react-i18next";

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showLoginIntro, setShowLoginIntro] = useState(false);
  const backgroundRef = useRef<HTMLDivElement | null>(null);
  const trailLayerRef = useRef<HTMLDivElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const loginIntroTimeoutRef = useRef<number | null>(null);
  const trailTimeoutsRef = useRef<number[]>([]);
  const trailSequenceRef = useRef(0);
  const pointerPositionRef = useRef({ x: 50, y: 50, px: 0, py: 0 });

  useEffect(() => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("user_role");
  }, []);

  useEffect(() => {
    return () => {
      if (animationFrameRef.current !== null) {
        window.cancelAnimationFrame(animationFrameRef.current);
      }

      if (loginIntroTimeoutRef.current !== null) {
        window.clearTimeout(loginIntroTimeoutRef.current);
      }

      trailTimeoutsRef.current.forEach((timeoutId) => {
        window.clearTimeout(timeoutId);
      });
    };
  }, []);

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    pointerPositionRef.current = {
      x: ((event.clientX - bounds.left) / bounds.width) * 100,
      y: ((event.clientY - bounds.top) / bounds.height) * 100,
      px: event.clientX - bounds.left,
      py: event.clientY - bounds.top,
    };

    if (animationFrameRef.current !== null) {
      return;
    }

    animationFrameRef.current = window.requestAnimationFrame(() => {
      const background = backgroundRef.current;
      const trailLayer = trailLayerRef.current;
      const { x, y, px, py } = pointerPositionRef.current;

      if (background) {
        background.style.setProperty("--cursor-x", `${x}%`);
        background.style.setProperty("--cursor-y", `${y}%`);
      }

      if (trailLayer) {
        const trail = document.createElement("span");
        const sequence = trailSequenceRef.current;
        const size = 6 + (sequence % 3) * 2;
        const isLightArea = x > 58;

        trailSequenceRef.current = sequence + 1;
        trail.className = "pointer-events-none absolute block";
        trail.style.left = `${px}px`;
        trail.style.top = `${py}px`;
        trail.style.width = `${size}px`;
        trail.style.height = `${size}px`;
        trail.style.marginLeft = `${size / -2}px`;
        trail.style.marginTop = `${size / -2}px`;
        trail.style.background = isLightArea
          ? "rgba(7, 26, 51, 0.92)"
          : "rgba(224, 242, 254, 0.96)";
        trail.style.boxShadow = isLightArea
          ? "0 0 10px rgba(18, 53, 91, 0.58), 0 0 22px rgba(15, 23, 42, 0.22)"
          : "0 0 10px rgba(125, 211, 252, 0.95), 0 0 26px rgba(56, 189, 248, 0.45)";
        trail.style.clipPath =
          "polygon(50% 0%, 61% 34%, 98% 35%, 68% 56%, 79% 91%, 50% 70%, 21% 91%, 32% 56%, 2% 35%, 39% 34%)";
        trail.style.transform = `rotate(${sequence * 23}deg)`;
        trail.style.animation = "cursorTrail 760ms ease-out forwards";

        trailLayer.appendChild(trail);

        const timeoutId = window.setTimeout(() => {
          trail.remove();
          trailTimeoutsRef.current = trailTimeoutsRef.current.filter((id) => id !== timeoutId);
        }, 780);

        trailTimeoutsRef.current.push(timeoutId);
      }

      animationFrameRef.current = null;
    });
  };

  const handleLogin = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.post("/token/", {
        username,
        password,
        platform: "web",
      });

      const data = response.data;
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("user_role", data.role);

      setShowLoginIntro(true);
      loginIntroTimeoutRef.current = window.setTimeout(() => {
        loginIntroTimeoutRef.current = null;
        setIsLoggedIn(true);
      }, 2600);
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    } finally {
      if (!loginIntroTimeoutRef.current) {
        setLoading(false);
      }
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

  const heroFeatures = [
    { icon: Package, label: t("auth.feature1"), index: "01" },
    { icon: RefreshCw, label: t("auth.feature2"), index: "02" },
    { icon: ShieldCheck, label: t("auth.feature3"), index: "03" },
  ];

  return (
    <div
      ref={backgroundRef}
      onPointerMove={handlePointerMove}
      className="relative min-h-screen overflow-hidden bg-[linear-gradient(128deg,#020817_0%,#06172e_28%,#12355b_50%,#e9f2fb_76%,#ffffff_100%)]"
      style={
        {
          "--cursor-x": "50%",
          "--cursor-y": "50%",
        } as React.CSSProperties
      }
    >
      <style>
        {`
          @keyframes cursorTrail {
            0% {
              opacity: 0.95;
              transform: translate3d(0, 0, 0) scale(1) rotate(0deg);
            }
            100% {
              opacity: 0;
              transform: translate3d(-18px, -16px, 0) scale(0.2) rotate(135deg);
            }
          }

          @keyframes bekoIntroOverlay {
            0% {
              opacity: 1;
            }
            72% {
              opacity: 1;
            }
            100% {
              opacity: 0;
              visibility: hidden;
            }
          }

          @keyframes bekoIntroLogo {
            0% {
              opacity: 0;
              letter-spacing: 0.28em;
              transform: scale(0.88);
              filter: blur(10px);
            }
            36% {
              opacity: 1;
              filter: blur(0);
            }
            72% {
              opacity: 1;
              letter-spacing: 0.16em;
              transform: scale(1);
            }
            100% {
              opacity: 0;
              letter-spacing: 0.2em;
              transform: scale(1.08);
              filter: blur(5px);
            }
          }

          @keyframes bekoIntroShine {
            0% {
              transform: translateX(-150%) skewX(-18deg);
              opacity: 0;
            }
            34% {
              opacity: 0;
            }
            52% {
              opacity: 0.95;
            }
            78% {
              transform: translateX(150%) skewX(-18deg);
              opacity: 0;
            }
            100% {
              transform: translateX(150%) skewX(-18deg);
              opacity: 0;
            }
          }
        `}
      </style>
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(2,8,23,0.96)_0%,rgba(6,23,46,0.9)_34%,rgba(18,53,91,0.58)_54%,rgba(255,255,255,0.66)_78%,rgba(255,255,255,0.95)_100%)]" />
      <div ref={trailLayerRef} className="pointer-events-none absolute inset-0 z-[1]" />
      <div
        className="pointer-events-none absolute inset-0 z-[2] opacity-75 transition-opacity duration-300"
        style={{
          background:
            "radial-gradient(56rem circle at var(--cursor-x) var(--cursor-y), rgba(125, 211, 252, 0.16), rgba(186, 230, 253, 0.08) 34%, rgba(255, 255, 255, 0.04) 52%, transparent 76%)",
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 z-[2] opacity-60 mix-blend-soft-light"
        style={{
          background:
            "linear-gradient(115deg, transparent 0%, rgba(255, 255, 255, 0.05) calc(var(--cursor-x) - 24%), rgba(125, 211, 252, 0.1) var(--cursor-x), transparent calc(var(--cursor-x) + 28%))",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-[90] flex items-center justify-center bg-[#020817]"
        style={{ animation: "bekoIntroOverlay 2600ms ease forwards" }}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.18),transparent_42%),linear-gradient(135deg,#020817_0%,#071a33_48%,#0f2f56_100%)]" />
        <div className="relative overflow-hidden px-10 py-6">
          <div
            className="text-6xl font-extrabold text-white md:text-8xl"
            style={{
              animation: "bekoIntroLogo 2600ms cubic-bezier(0.22, 1, 0.36, 1) forwards",
              textShadow:
                "0 0 18px rgba(186, 230, 253, 0.35), 0 18px 44px rgba(0, 0, 0, 0.35)",
            }}
          >
            BEKO SIRS
          </div>
          <span
            className="absolute inset-y-4 left-0 w-1/2 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.86),transparent)]"
            style={{ animation: "bekoIntroShine 2600ms ease forwards" }}
          />
        </div>
      </div>
      {showLoginIntro && (
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 z-[90] flex items-center justify-center bg-[#020817]"
          style={{ animation: "bekoIntroOverlay 2600ms ease forwards" }}
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.18),transparent_42%),linear-gradient(135deg,#020817_0%,#071a33_48%,#0f2f56_100%)]" />
          <div className="relative overflow-hidden px-10 py-6">
            <div
              className="text-6xl font-extrabold text-white md:text-8xl"
              style={{
                animation: "bekoIntroLogo 2600ms cubic-bezier(0.22, 1, 0.36, 1) forwards",
                textShadow:
                  "0 0 18px rgba(186, 230, 253, 0.35), 0 18px 44px rgba(0, 0, 0, 0.35)",
              }}
            >
              BEKO SIRS
            </div>
            <span
              className="absolute inset-y-4 left-0 w-1/2 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.86),transparent)]"
              style={{ animation: "bekoIntroShine 2600ms ease forwards" }}
            />
          </div>
        </div>
      )}

      <div className="absolute left-0 right-0 top-0 z-50 flex justify-end px-4 py-4">
        <div className="flex gap-2 rounded-lg border border-white/60 bg-white/70 p-1 shadow-sm backdrop-blur-md">
          <button
            onClick={() => i18n.changeLanguage("tr")}
            className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
              i18n.language === "tr"
                ? "bg-[#12355b] text-white shadow-sm"
                : "text-slate-700 hover:bg-white"
            }`}
          >
            TR
          </button>
          <button
            onClick={() => i18n.changeLanguage("en")}
            className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
              i18n.language === "en"
                ? "bg-[#12355b] text-white shadow-sm"
                : "text-slate-700 hover:bg-white"
            }`}
          >
            EN
          </button>
        </div>
      </div>

      <main className="relative z-10 grid min-h-screen grid-cols-1 items-center gap-10 px-6 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:px-16 xl:px-24">
        <section className="hidden min-h-[620px] flex-col justify-center text-white lg:flex">
          <div className="max-w-xl">
            <div className="mb-10 inline-flex rounded-lg bg-white px-6 py-3 text-3xl font-bold text-[#071a33] shadow-lg shadow-slate-950/10">
              BEKO SIRS
            </div>

            <h1
              className="mb-6 text-5xl font-bold leading-tight text-white"
              dangerouslySetInnerHTML={{ __html: t("auth.heroTitle") }}
            />

            <p
              className="mb-10 text-xl leading-relaxed text-blue-50/90"
              dangerouslySetInnerHTML={{ __html: t("auth.heroDesc") }}
            />

            <div className="grid max-w-lg grid-cols-1 gap-3">
              {heroFeatures.map(({ icon: Icon, label, index }) => (
                <div
                  key={index}
                  className="group flex items-center gap-4 rounded-lg border border-white/15 bg-white/[0.08] p-3 shadow-lg shadow-slate-950/10 backdrop-blur-md transition hover:border-sky-200/50 hover:bg-white/[0.13]"
                >
                  <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg border border-sky-200/25 bg-sky-100/10 text-sky-100">
                    <Icon size={22} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="h-px w-10 bg-sky-200/50 transition group-hover:w-16" />
                    <p className="mt-2 truncate text-base font-semibold text-white">
                      {label}
                    </p>
                  </div>
                  <span className="text-sm font-semibold tracking-[0.18em] text-sky-100/70">
                    {index}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center">
          <div className="w-full max-w-md">
            <div className="rounded-lg border border-white/80 bg-white/90 p-8 shadow-2xl shadow-slate-900/15 backdrop-blur-xl">
              <div className="mb-8 text-center">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-lg bg-[#12355b] shadow-lg shadow-blue-950/20">
                  <Lock size={32} className="text-white" />
                </div>
                <h2 className="mb-2 text-3xl font-bold text-slate-950">
                  {t("auth.loginTitle")}
                </h2>
                <p className="text-slate-600">{t("auth.loginSubtitle")}</p>
              </div>

              {error && (
                <div className="mb-6 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
                  <AlertCircle size={20} className="mt-0.5 flex-shrink-0 text-red-500" />
                  <p className="text-sm font-medium text-red-600">{error}</p>
                </div>
              )}

              <div className="space-y-5">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">
                    {t("auth.lblUsername")}
                  </label>
                  <div className="relative">
                    <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      onKeyPress={handleKeyPress}
                      className="w-full rounded-lg border border-slate-200 bg-white/95 py-3 pl-12 pr-4 text-slate-900 shadow-sm transition-all placeholder:text-slate-400 focus:border-[#1f4e79] focus:outline-none focus:ring-4 focus:ring-blue-100"
                      placeholder={t("auth.plcUsername")}
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">
                    {t("auth.lblPassword")}
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onKeyPress={handleKeyPress}
                      className="w-full rounded-lg border border-slate-200 bg-white/95 py-3 pl-12 pr-12 text-slate-900 shadow-sm transition-all placeholder:text-slate-400 focus:border-[#1f4e79] focus:outline-none focus:ring-4 focus:ring-blue-100"
                      placeholder={"\u2022".repeat(8)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-[#12355b]"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </div>

                <button
                  onClick={handleLogin}
                  disabled={loading || !username || !password}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#12355b] py-3 font-semibold text-white shadow-lg shadow-blue-950/20 transition-all hover:bg-[#0b2747] disabled:opacity-50"
                >
                  {loading ? (
                    <div className="h-5 w-5 animate-spin rounded-full border-b-2 border-white" />
                  ) : (
                    <>
                      <LogIn size={20} />
                      <span>{t("auth.btnLogin")}</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <p className="mt-8 text-center text-sm text-slate-500">
              {"\u00A9"} 2025 Beko Kurumsal.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
