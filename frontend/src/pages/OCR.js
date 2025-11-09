import React, { useState } from "react";
import { useApi } from "../services/api";
import "../styles/page-ocr.css";

export default function OCR() {
  const api = useApi();
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState("text");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (!file) return;
    setOut("");
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    form.append("mode", mode);

    try {
      const { data } = await api.post("/ocr", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setOut(data.text);
    } catch (err) {
      console.error("OCR error:", err);
      setOut("Error processing image.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page ocr">
      <h2>Image OCR / Description</h2>
      <div className="card">
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="text">Extract Text Only</option>
          <option value="describe">Detailed Description</option>
        </select>
        <button onClick={run} disabled={!file || busy}>
          {busy ? "Processing…" : "Run"}
        </button>
      </div>
      <pre className="output">{out}</pre>
    </div>
  );
}
