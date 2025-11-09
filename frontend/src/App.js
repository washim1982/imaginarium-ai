import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import ModelHub from "./pages/ModelHub";
import Training from "./pages/Training";
import SqlTrainer from "./pages/SqlTrainer";
import Analysis from "./pages/Analysis";
import OCR from "./pages/OCR";
import Rag from "./pages/Rag";
import Translation from "./pages/Translation";
import CodeFix from "./pages/CodeFix";
import { useAuth0 } from "@auth0/auth0-react";
import "./App.css";
import { applyTheme, getTheme } from "./theme";

export default function App() {
  const { isAuthenticated, isLoading, loginWithRedirect, logout, user } = useAuth0();
  const [menuOpen, setMenuOpen] = React.useState(true);
  const [theme, setTheme] = React.useState(getTheme());

  React.useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth < 900) {
      setMenuOpen(false);
    }
    // Apply persisted theme on first load
    try { applyTheme(theme); } catch {}
  }, []);

  React.useEffect(() => {
    try { applyTheme(theme); } catch {}
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "light" ? "dark" : "light"));

  const layoutClass = `layout ${menuOpen ? "sidebar-open" : "sidebar-collapsed"}`;

  if (isLoading) return <div className="loading">Loading...</div>;

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <button
            className="menu-toggle"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
          >
            {menuOpen ? "☰" : "☰"}
          </button>
          <span className="brand">Imaginarium AI</span>
        </div>

        <div className="header-right">
          <button
            onClick={toggleTheme}
            className="auth-btn"
            title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
            aria-label="Toggle theme"
          >
            {theme === "light" ? "🌙 Dark" : "☀️ Light"}
          </button>
          {isAuthenticated ? (
            <>
              <span style={{ marginRight: "10px" }}>{user?.email}</span>
              <button
                onClick={() =>
                  logout({ logoutParams: { returnTo: window.location.origin } })
                }
                className="auth-btn"
              >
                Logout
              </button>
            </>
          ) : (
            <button
              onClick={() => loginWithRedirect()}
              className="auth-btn"
            >
              Login
            </button>
          )}
        </div>
      </header>

      {/* Sidebar + Main content */}
      <div className={layoutClass}>
        <Sidebar menuOpen={menuOpen} setMenuOpen={setMenuOpen} />

        <main className="main-content">
          <Routes>
            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/models" replace />} />

            {/* App pages */}
            <Route path="/models" element={<ModelHub />} />
            <Route path="/training" element={<Training />} />
            <Route path="/sql-trainer" element={<SqlTrainer />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/ocr" element={<OCR />} />
            <Route path="/rag" element={<Rag />} />
            <Route path="/translation" element={<Translation />} />
            <Route path="/code-fix" element={<CodeFix />} />
            <Route
              path="/settings"
              element={
                <React.Suspense fallback={<div />}> 
                  <SettingsLazy />
                </React.Suspense>
              }
            />

            {/* 404 fallback */}
            <Route path="*" element={<div>Page not found</div>} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

// Lazy import settings to avoid increasing initial bundle too much
const SettingsLazy = React.lazy(() => import("./pages/Settings"));
