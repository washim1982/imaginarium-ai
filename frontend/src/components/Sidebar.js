import React from "react";
import { Link, useLocation } from "react-router-dom";
import { FiCpu, FiSliders, FiCode, FiBarChart2, FiImage, FiFileText, FiGlobe } from "react-icons/fi";
import "./Sidebar.css";

export default function Sidebar({ menuOpen, setMenuOpen }) {
  const location = useLocation();

  const links = [
    { path: "/models", label: "Model Hub", icon: FiCpu },
    { path: "/training", label: "Custom Model Training", icon: FiSliders },
    { path: "/sql-trainer", label: "SQL Trainer", icon: FiCode },
    { path: "/analysis", label: "File Analytics", icon: FiBarChart2 },
    { path: "/ocr", label: "Image OCR", icon: FiImage },
    { path: "/rag", label: "Chat with Document", icon: FiFileText },
    { path: "/translation", label: "Translate & Summarize", icon: FiGlobe },
    { path: "/code-fix", label: "Code Fix", icon: FiCode },
    { path: "/settings", label: "Settings", icon: FiSliders },
  ];

  return (
    <aside className={`sidebar ${menuOpen ? "expanded" : "collapsed"}`}>
      <div className="sidebar-content">
        {links.map(({ path, label, icon: Icon }) => (
          <Link
            key={path}
            to={path}
            className={location.pathname === path ? "active" : ""}
            aria-label={label}
            onClick={() => setMenuOpen(false)}
          >
            <Icon className="sidebar-icon" aria-hidden="true" />
            <span className="sidebar-label">{label}</span>
          </Link>
        ))}
      </div>
    </aside>
  );
}
