import React, { useEffect, useRef, useState } from "react";
import { useApi } from "../services/api";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import "../styles/page-codefix.css";

const LANGUAGE_MAP = {
  js: "javascript",
  jsx: "javascript",
  ts: "typescript",
  tsx: "tsx",
  py: "python",
  rb: "ruby",
  java: "java",
  go: "go",
  rs: "rust",
  cpp: "cpp",
  c: "c",
  cs: "csharp",
  php: "php",
  swift: "swift",
  kt: "kotlin",
};

function guessLanguage(filename = "") {
  const ext = filename.split(".").pop();
  return LANGUAGE_MAP[ext] || "text";
}

export default function CodeFix() {
  const api = useApi();
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [summary, setSummary] = useState("");
  const [fixedCode, setFixedCode] = useState("");
  const [originalCode, setOriginalCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const DEFAULT_CODE_MODEL = "codellama:7b-instruct";
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(DEFAULT_CODE_MODEL);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await api.get("/models");
        if (mounted) {
          const list = res.data.models || [];
          setModels(list);
          setSelectedModel((prev) => prev || list[0] || DEFAULT_CODE_MODEL);
        }
      } catch (err) {
        console.warn("Unable to load models", err);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [api]);

  const triggerUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const inputEl = event.target;
    setSelectedFile(file);
    setError("");
    setSummary("");
    setFixedCode("");
    setOriginalCode("");
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = typeof ev.target?.result === "string" ? ev.target.result : "";
      setOriginalCode(text);
    };
    reader.onerror = () => {
      setOriginalCode("");
      setError("Unable to preview file.");
    };
    reader.readAsText(file);
    // Reset the input so selecting the same file again still triggers change.
    if (inputEl) {
      inputEl.value = "";
    }
  };

  const runAgent = async () => {
    if (!selectedFile) {
      setError("Upload a file before running the agent.");
      return;
    }
    await processFile(selectedFile);
  };

  const processFile = async (file) => {
    setLoading(true);
    try {
      const data = new FormData();
      data.append("file", file);
      data.append("model", selectedModel);
      const response = await api.post("/codefix", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setSummary(response.data.summary);
      setFixedCode(response.data.fixed_code);
    } catch (err) {
      console.error(err);
      setError(err?.response?.data?.detail || "Unable to process file.");
    } finally {
      setLoading(false);
    }
  };

  const copyFixed = async () => {
    if (!fixedCode) return;
    await navigator.clipboard.writeText(fixedCode);
  };

  const downloadFixed = () => {
    if (!fixedCode || !selectedFile) return;
    const blob = new Blob([fixedCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const parts = selectedFile.name.split(".");
    const ext = parts.length > 1 ? parts.pop() : "txt";
    a.download = `${parts.join(".") || "codefix-output"}.fixed.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const language = guessLanguage(selectedFile?.name);

  return (
    <div className="page codefix-page">
      <section className="codefix-section controls">
        <h2>Code Fix Agent</h2>
        <p>Upload a file, choose a model, and run the agent to receive fixes and a summary.</p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".js,.jsx,.ts,.tsx,.py,.rb,.java,.go,.rs,.cpp,.c,.cs,.php,.swift,.kt,.json,.txt"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        <div className="controls-row">
          <div className="control-group">
            <label className="model-label" htmlFor="model-select">
              Agent Model
            </label>
            <select
              id="model-select"
              className="model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={!models.length || loading}
            >
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div className="control-group">
            <label className="model-label">&nbsp;</label>
            <button className="upload-btn" onClick={triggerUpload} disabled={loading}>
              {selectedFile ? "Re-upload" : "Upload"}
            </button>
          </div>
          <div className="control-group">
            <label className="model-label">&nbsp;</label>
            <button className="run-btn" onClick={runAgent} disabled={!selectedFile || loading}>
              {loading ? "Running..." : "Run Agent"}
            </button>
          </div>
        </div>
        {selectedFile && (
          <p className="file-meta">
            <strong>File:</strong> {selectedFile.name}
          </p>
        )}
        {loading && <p className="status">Running agent...</p>}
        {error && <p className="status error">{error}</p>}
        {summary && (
          <div className="summary-box">
            <h3>Agent Summary</h3>
            <p>{summary}</p>
          </div>
        )}
        {fixedCode && (
          <div className="codefix-actions">
            <button onClick={copyFixed}>Copy Code</button>
            <button onClick={downloadFixed}>Download</button>
          </div>
        )}
      </section>

      <section className="codefix-section code-viewer">
        <div className="code-view__header">
          Original Code {selectedFile ? `- ${selectedFile.name}` : ""}
        </div>
        <div className="code-view__body">
          <SyntaxHighlighter
            language={language}
            style={oneDark}
            showLineNumbers
            wrapLines
            customStyle={{
              background: "transparent",
              minHeight: "220px",
              boxShadow: "none",
            }}
          >
            {originalCode || "// Upload a file to see the original code here."}
          </SyntaxHighlighter>
        </div>
      </section>

      <section className="codefix-section code-viewer">
        <div className="code-view__header">Fixed Code Output</div>
        <div className="code-view__body">
          <SyntaxHighlighter
            language={language}
            style={oneDark}
            showLineNumbers
            wrapLines
            customStyle={{
              background: "transparent",
              minHeight: "220px",
              boxShadow: "none",
            }}
          >
            {fixedCode || "// Run the agent to see the fixed code here."}
          </SyntaxHighlighter>
        </div>
      </section>
    </div>
  );
}
