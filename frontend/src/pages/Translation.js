import React, { useState } from "react";
import { useApi } from "../services/api";
import { useAuth0 } from "@auth0/auth0-react";
import "../styles/page-translation.css";

const LANGUAGES = [
  "English",
  "Arabic",
  "Spanish",
  "French",
  "German",
  "Hindi",
  "Japanese",
  "Chinese",
  "Portuguese",
];

export default function Translation() {
  const api = useApi();
  const { isAuthenticated, loginWithRedirect } = useAuth0();
  const [file, setFile] = useState(null);
  const [language, setLanguage] = useState("English");
  const [original, setOriginal] = useState("");
  const [translation, setTranslation] = useState("");
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!isAuthenticated) {
    return (
      <div style={{ padding: 24 }}>
        <h3>Translate & Summarize</h3>
        <p>You need to sign in to use this feature.</p>
        <button
          onClick={() =>
            loginWithRedirect({
              authorizationParams: {
                audience: process.env.REACT_APP_AUTH0_AUDIENCE,
                scope: "openid profile email",
                prompt: "login",
              },
            })
          }
        >
          Login
        </button>
      </div>
    );
  }

  const run = async () => {
    if (!file) return;
    setBusy(true);
    setError("");
    setTranslation("");
    setSummary("");

    let preview = "";
    if (file.type.startsWith("text/") || file.name.toLowerCase().endsWith(".txt")) {
      preview = await file.text();
    } else {
      preview = "Preview available after processing.";
    }
    setOriginal(preview);

    const form = new FormData();
    form.append("file", file);
    form.append("language", language);

    try {
      const { data } = await api.post("/translation", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setOriginal(data.original || preview);
      setTranslation(data.translation || "");
      setSummary(data.summary || "");
    } catch (err) {
      console.error("Translation error:", err);
      setError(
        err?.response?.data?.detail ||
          "Translation failed. Ensure the file is under 20MB and fewer than 10 pages."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page translation">
      <h2>Translate & Summarize</h2>
      {error && <p className="error-msg">{error}</p>}
      <div className="translator-controls">
        <div className="card upload-card">
          <input
            type="file"
            accept=".txt,.docx,.pdf"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
          <button onClick={run} disabled={!file || busy}>
            {busy ? "Processing…" : "Run"}
          </button>
        </div>
        <p className="note">
          Upload up to 20MB (.txt, .docx, .pdf). Summary is always returned in English.
        </p>

        <div className="triple">
          <div>
            <label>Original (Arabic)</label>
            <textarea readOnly value={original}></textarea>
          </div>
          <div>
            <label>Translation (English)</label>
            <textarea readOnly value={translation}></textarea>
          </div>
          <div>
            <label>Summary</label>
            <textarea readOnly value={summary}></textarea>
          </div>
        </div>
      </div>
    </div>
  );
}
