import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { atomDark } from "react-syntax-highlighter/dist/esm/styles/prism";

const prettyLang = (lang) => {
  const l = (lang || "").toLowerCase();
  const map = {
    js: "JavaScript",
    javascript: "JavaScript",
    jsx: "JSX",
    ts: "TypeScript",
    tsx: "TSX",
    py: "Python",
    python: "Python",
    sh: "Bash",
    bash: "Bash",
    shell: "Bash",
    zsh: "Zsh",
    json: "JSON",
    yaml: "YAML",
    yml: "YAML",
    md: "Markdown",
    markdown: "Markdown",
    html: "HTML",
    css: "CSS",
    scss: "SCSS",
    sql: "SQL",
    java: "Java",
    c: "C",
    cpp: "C++",
    csharp: "C#",
    cs: "C#",
    go: "Go",
    rust: "Rust",
    php: "PHP",
    ruby: "Ruby",
    kotlin: "Kotlin",
    swift: "Swift",
    plsql: "PL/SQL",
    sqlpl: "PL/SQL",
    powershell: "PowerShell",
    ps1: "PowerShell",
    xml: "XML",
    toml: "TOML",
    ini: "INI",
    dockerfile: "Dockerfile",
  };
  return map[l] || (lang ? lang.toUpperCase() : "plaintext");
};

const CodeBlock = ({ inline, className, children, ...props }) => {
  const match = /language-(\w+)/.exec(className || "");
  const language = match ? match[1] : "text"; // default to plaintext when not specified
  const content = String(children).replace(/\n$/, "");
  const [copied, setCopied] = useState(false);

  if (inline) {
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch (err) {
      console.error("Copy failed", err);
    }
  };

  return (
    <div className="code-block">
      <span className="lang-badge" aria-label={`Code language: ${prettyLang(language)}`}>
        {prettyLang(language)}
      </span>
      <button type="button" className="copy-btn" onClick={handleCopy}>
        {copied ? "Copied" : "Copy"}
      </button>
      <SyntaxHighlighter style={atomDark} language={language} PreTag="div" {...props}>
        {content}
      </SyntaxHighlighter>
    </div>
  );
};

export default function MarkdownMessage({ text }) {
  // Heuristic: auto-fence obvious code paragraphs if the model forgot backticks
  const autoFence = (raw) => {
    if (!raw || raw.includes("```")) return raw;
    const langs = [
      { id: "plsql", rx: /\b(CREATE\s+OR\s+REPLACE\s+PROCEDURE|DECLARE|BEGIN|EXCEPTION|END;|EXECUTE\s+IMMEDIATE)\b/i },
      { id: "sql", rx: /\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|FROM|WHERE|JOIN|GROUP\s+BY|ORDER\s+BY)\b/i },
      { id: "python", rx: /\b(def|class|import|from|return|self|print\()\b/ },
      { id: "javascript", rx: /\b(function|const|let|var|=>|console\.log\()\b/ },
      { id: "typescript", rx: /\b(interface|type\s+\w+\s*=|:\s*\w+\s*[;=])\b/ },
      { id: "java", rx: /\b(public|private|protected|class|static|void|new\s+\w+\()\b/ },
      { id: "csharp", rx: /\b(namespace|using\s+System|public\s+class|Task<)\b/ },
      { id: "cpp", rx: /#include\s*<|\bstd::|template<|::/ },
      { id: "c", rx: /#include\s*<|\bint\s+main\s*\(/ },
      { id: "go", rx: /\bpackage\s+main\b|\bfunc\s+\w+\(|\bfmt\.Print/ },
      { id: "rust", rx: /\bfn\s+\w+\s*\(|::|let\s+mut\b/ },
      { id: "php", rx: /<\?php|\$\w+\s*=|echo\s+\w+/ },
      { id: "ruby", rx: /\bdef\s+\w+|end\b|puts\s+\w+/ },
      { id: "kotlin", rx: /\bfun\s+\w+\(|val\s+\w+|var\s+\w+/ },
      { id: "swift", rx: /\bfunc\s+\w+\(|let\s+\w+|var\s+\w+/ },
      { id: "json", rx: /\{\s*"[^"]+"\s*:/ },
      { id: "yaml", rx: /^\s*\w+\s*:\s*\S/m },
      { id: "xml", rx: /<\?xml|<\w+[\s>]/ },
      { id: "html", rx: /<(div|span|script|style|html|head|body)\b/ },
      { id: "css", rx: /\b[a-zA-Z0-9_-]+\s*\{[^}]*\}/ },
      { id: "toml", rx: /^\s*\[[^\]]+\]/m },
      { id: "ini", rx: /^\s*\[[^\]]+\]\s*$/m },
      { id: "bash", rx: /(^|\n)\s*\$\s*\w+|\b#!/ },
      { id: "powershell", rx: /\bGet-\w+|Set-\w+|Write-Host\b/ },
    ];
    const blocks = raw.split(/\n\s*\n/); // paragraphs
    let changed = false;
    const processed = blocks.map((p) => {
      const lines = p.split("\n");
      const codeyLines = lines.filter((l) => /[;{}()=<>]|\bEND\b|\bBEGIN\b|=>|::|#include|^\s{4,}/i.test(l)).length;
      const symbolDensity = codeyLines / Math.max(1, lines.length);
      const lang = langs.find((l) => l.rx.test(p));
      if ((lang || symbolDensity >= 0.45) && lines.length >= 2) {
        changed = true;
        const tag = lang ? lang.id : "text";
        return "```" + tag + "\n" + p + "\n```";
      }
      return p;
    });
    return changed ? processed.join("\n\n") : raw;
  };

  const textProcessed = autoFence(text);
  return (
    <ReactMarkdown
      components={{
        code: CodeBlock,
      }}
    >
      {textProcessed}
    </ReactMarkdown>
  );
}
