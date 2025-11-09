export const THEME_KEY = "app_theme";

export function getTheme() {
  if (typeof window === "undefined") return "dark";
  const saved = window.localStorage.getItem(THEME_KEY);
  return saved === "light" || saved === "dark" ? saved : "dark";
}

export function applyTheme(theme) {
  if (typeof document === "undefined") return;
  const t = theme === "light" ? "light" : "dark";
  document.body.classList.remove("theme-light", "theme-dark");
  document.body.classList.add(t === "light" ? "theme-light" : "theme-dark");
  try { window.localStorage.setItem(THEME_KEY, t); } catch {}
}

