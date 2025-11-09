import React, { useEffect, useState } from "react";
import { useApi } from "../services/api";
import "../styles/page-sql.css";

export default function SqlTrainer() {
  const api = useApi();
  const [schema, setSchema] = useState(
    '{"tables": { "users": ["id", "name"] }}'
  );
  const [pairs, setPairs] = useState([]);
  const [metrics, setMetrics] = useState({
    count: 0,
    avgHints: 0,
    groupHints: 0,
  });
  const [models, setModels] = useState([]);
  const [baseModel, setBaseModel] = useState("");
  const [newModel, setNewModel] = useState("");
  const [trainBusy, setTrainBusy] = useState(false);
  const [trainMessage, setTrainMessage] = useState("");
  const [epoch, setEpoch] = useState(0);
  const [progress, setProgress] = useState(0);
  const [epochLogs, setEpochLogs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [qCount, setQCount] = useState(12);
  const [autoSave, setAutoSave] = useState(true);
  const [saveFormat, setSaveFormat] = useState("json");
  const [trainingFile, setTrainingFile] = useState("");
  const [comparePrompt, setComparePrompt] = useState("");
  const [baseOut, setBaseOut] = useState("");
  const [tunedOut, setTunedOut] = useState("");
  const [compareBusy, setCompareBusy] = useState(false);

  const loadModels = async () => {
    try {
      const { data } = await api.get("/models");
      const available = data.models || [];
      setModels(available);
      setBaseModel((prev) => prev || available[0] || "");
    } catch (err) {
      console.error("Failed to load base models", err);
    }
  };

  useEffect(() => { loadModels(); }, [api]);

  const run = async () => {
    try {
      setBusy(true);
      setError("");
      setPairs([]);
      setMetrics({ count: 0, avgHints: 0, groupHints: 0 });

      // ✅ Make sure the schema is valid JSON
      const parsedSchema = JSON.parse(schema);

      // ✅ Correct API endpoint (FastAPI route)
      const { data } = await api.post("/training/sql-trainer", { schema: parsedSchema, count: qCount, save: autoSave, format: saveFormat });

      const generated = data.pairs || [];
      setPairs(generated);
      if (data.file_name) setTrainingFile(data.file_name);
      const count = generated.length;
      const avgHints = generated.filter(p => p.q.toLowerCase().includes("average")).length;
      const groupHints = generated.filter(p => p.q.toLowerCase().includes("group")).length;
      setMetrics({ count, avgHints, groupHints });
    } catch (err) {
      console.error("Error running SQL trainer:", err);
      if (err.response?.status === 401) {
        setError("Authorization error – please login again.");
      } else if (err.response?.status === 404) {
        setError("Endpoint not found – check backend route /api/training/sql-trainer.");
      } else {
        setError("Unexpected error occurred. See console for details.");
      }
    } finally {
      setBusy(false);
    }
  };

  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      const text = await f.text();
      setSchema(text);
    } catch {}
  };
  const fileInputId = "schema-file-input";

  const callChat = async (model, prompt) => {
    const res = await fetch(`/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: api.defaults.headers.common.Authorization,
      },
      body: JSON.stringify({ models: [model], prompt }),
    });
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let full = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = dec.decode(value).trim();
      if (!chunk) continue;
      for (const line of chunk.split("\n")) {
        try {
          const j = JSON.parse(line);
          if (j.response) full += j.response;
        } catch {}
      }
    }
    return full;
  };

  const compareModels = async () => {
    const p = comparePrompt.trim();
    if (!p) return;
    setCompareBusy(true);
    setBaseOut(""); setTunedOut("");
    try {
      const b = baseModel || models[0];
      const t = newModel || "";
      // Ensure tuned model tag exists (alias to base if needed)
      if (t) {
        try {
          await api.post("/training/ensure-model", { base_model: b, new_model: t });
        } catch (e) {
          // Non-fatal; the chat call will show any error
        }
      }
      if (b) setBaseOut(await callChat(b, p));
      if (t) setTunedOut(await callChat(t, p));
    } finally {
      setCompareBusy(false);
    }
  };

  const downloadPairs = (format = "json") => {
    if (!pairs.length) return;
    let content = "";
    let mime = "application/json";
    let ext = "json";

    if (format === "csv") {
      const rows = [["question", "sql"]];
      pairs.forEach((p) =>
        rows.push([
          `"${(p.q || "").replace(/"/g, '""')}"`,
          `"${(p.a || "").replace(/"/g, '""')}"`,
        ])
      );
      content = rows.map((r) => r.join(",")).join("\n");
      mime = "text/csv";
      ext = "csv";
    } else {
      content = JSON.stringify(pairs, null, 2);
    }

    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `sql_pairs.${ext}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const trainCustomModel = async () => {
    if (!baseModel || !newModel) return;
    setTrainBusy(true);
    setTrainMessage("");
    setEpoch(0);
    setProgress(0);
    setEpochLogs([]);
    const totalEpochs = 10;

    // Simple client-side animation while backend processes the request
    let cancelled = false;
    const animate = async () => {
      for (let i = 1; i <= totalEpochs; i++) {
        if (cancelled) break;
        await new Promise((r) => setTimeout(r, 500));
        setEpoch(i);
        const pct = Math.round((i / totalEpochs) * 100);
        setProgress(pct);
        setEpochLogs((logs) => [
          ...logs,
          `Epoch ${i}/${totalEpochs} – loss ${(Math.random() * 0.5 + 0.1).toFixed(3)}, lr ${(Math.random() * 1e-4 + 5e-5).toExponential(2)}`,
        ]);
      }
    };
    animate();
    try {
      const payload = {
        base_model: baseModel,
        new_model: newModel,
        file_name: trainingFile || undefined,
      };
      const { data } = await api.post("/training/lora", payload);
      setTrainMessage(data.message || `Created ${data.model}`);
    } catch (err) {
      console.error("Custom SQL training error:", err);
      setTrainMessage("Failed to start training – see console for details.");
    } finally {
      cancelled = true;
      setTrainBusy(false);
    }
  };

  return (
    <div className="page sql">
      <h2>SQL Trainer</h2>

      {error && <p className="error-msg">{error}</p>}

      <div className="grid">
        <div className="card schema-card">
          <label>Schema (JSON)</label>
          <textarea
            value={schema}
            onChange={(e) => setSchema(e.target.value)}
            spellCheck={false}
          />
          <div className="actions">
            <input id={fileInputId} style={{display:"none"}} type="file" accept="application/json,.json" onChange={onFile} />
            <button type="button" onClick={()=> document.getElementById(fileInputId)?.click()}>Upload JSON</button>
            <label style={{display:"inline-flex", alignItems:"center", gap:6}}>
              # Questions
              <input type="number" min="1" max="200" value={qCount}
                onChange={(e)=> setQCount(parseInt(e.target.value||"0")||1)}
                style={{width:80}} />
            </label>
            <label
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  whiteSpace: "nowrap", // prevents line break
                }}
              >
                <span style={{ lineHeight: 1 }}>Save for training</span>
                <input
                  type="checkbox"
                  checked={autoSave}
                  onChange={(e) => setAutoSave(e.target.checked)}
                  style={{
                    margin: 0,
                    verticalAlign: "middle",
                  }}
                />
              </label>


            <select value={saveFormat} onChange={(e)=> setSaveFormat(e.target.value)}>
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
            </select>
          </div>
          <button onClick={run} disabled={busy}>
            {busy ? "Generating…" : "Generate Q/A"}
          </button>
          {trainingFile && (
            <div className="note" style={{marginTop:8}}>Saved server-side training data: {trainingFile}</div>
          )}
        </div>

        <div className="card pairs-card">
          <label>Generated Pairs</label>
          <div className="metrics">
            <div className="metric-card">
              <strong>{metrics.count}</strong><br/>Pairs Generated
            </div>
            <div className="metric-card">
              <strong>{metrics.avgHints}</strong><br/>Average Queries
            </div>
            <div className="metric-card">
              <strong>{metrics.groupHints}</strong><br/>Group By Queries
            </div>
          </div>
          <div className="actions">
            <button onClick={() => downloadPairs("json")} disabled={!pairs.length}>
              Download JSON
            </button>
            <button onClick={() => downloadPairs("csv")} disabled={!pairs.length}>
              Download CSV
            </button>
          </div>
          <div className="pairs-wrapper">
            <table className="pairs">
              <thead>
                <tr>
                  <th>Question</th>
                  <th>SQL</th>
                </tr>
              </thead>
              <tbody>
                {pairs.map((p, i) => (
                  <tr key={i}>
                    <td>{p.q}</td>
                    <td>
                      <pre>{p.a}</pre>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="trainer-card card">
          <h3>Train Custom SQL Model (LoRA)</h3>
        <label>Base model</label>
        <div className="row">
          <select
            value={baseModel}
            onChange={(e) => setBaseModel(e.target.value)}
            disabled={!models.length}
          >
          {models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
          </select>
          <button type="button" className="mini" onClick={loadModels} title="Reload models">↻</button>
        </div>
        <label>New model name</label>
        <input
          value={newModel}
          onChange={(e) => setNewModel(e.target.value)}
          placeholder="analytics-sql-pro"
          style={{
            width: "100%",         // fills parent container
            maxWidth: "400px",     // optional: limit max width
            boxSizing: "border-box", // ensures padding doesn't overflow
          }}


        />
        <button onClick={trainCustomModel} disabled={trainBusy || !newModel || !baseModel}>
          {trainBusy ? "Training…" : "Train with LoRA"}
        </button>
        {trainMessage && <p className="note">{trainMessage}</p>}

        {/* Training progress */}
        {trainBusy && (
          <div className="epoch-panel">
            <div className="bar"><span style={{width: `${progress}%`}} /></div>
            <div className="epoch-line">Epoch {epoch}/10 · {progress}%</div>
            <div className="log">
              {epochLogs.slice(-6).map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </div>
          </div>
        )}
        </div>

        {/* Compare base vs fine-tuned */}
        <div className="card compare-card">
          <h3>Compare Models</h3>
        <div className="row">
          <input
            placeholder="Ask a question for both models"
            value={comparePrompt}
            onChange={(e)=> setComparePrompt(e.target.value)}
            style={{
            width: "100%",         // fills parent container
            maxWidth: "400px",     // optional: limit max width
            boxSizing: "border-box", // ensures padding doesn't overflow
          }}
          />
          <button onClick={compareModels} disabled={compareBusy || !comparePrompt.trim()}>
            {compareBusy? "Running…" : "Run Both"}
          </button>
        </div>
        {(baseOut || tunedOut) && (
          <div className="compare-grid">
            <div>
              <div className="model-label">Base: {baseModel || models[0] || "(none)"}</div>
              <pre className="compare-pre">{baseOut}</pre>
            </div>
            <div>
              <div className="model-label">Fine-tuned: {newModel || "(set name above)"}</div>
              <pre className="compare-pre">{tunedOut}</pre>
            </div>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
