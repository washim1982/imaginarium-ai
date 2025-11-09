import React, { useEffect, useState } from "react";
import { applyTheme, getTheme } from "../theme";
import "../styles/page-settings.css";

export default function Settings() {
  const [theme, setTheme] = useState(getTheme());

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return (
    <div className="page" style={{ maxWidth: 720 }}>
      <h2>Settings</h2>

      <div className="settings-card card">
        <h3 className="settings-title">Theme</h3>
        <div className="theme-options">
          <label className="theme-option">
            <input
              type="radio"
              name="theme"
              checked={theme === "dark"}
              onChange={() => setTheme("dark")}
            />
            <span>Dark (default)</span>
          </label>
          <label className="theme-option">
            <input
              type="radio"
              name="theme"
              checked={theme === "light"}
              onChange={() => setTheme("light")}
            />
            <span>Light (glass effect)</span>
          </label>
        </div>
        <p className="settings-note">
          Light theme uses a glassy backdrop with black text across the app.
        </p>
      </div>
    </div>
  );
}
