import React, { useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import "../styles/page-rag.css";


export default function Rag(){
const { getAccessTokenSilently } = useAuth0();
const [file, setFile] = useState(null);
const [uploaded, setUploaded] = useState(false);
const [question, setQuestion] = useState("");
const [answer, setAnswer] = useState("");
const [busy, setBusy] = useState(false);


const upload = async () => {
if(!file) return;
setBusy(true);
const token = await getAccessTokenSilently();
const form = new FormData(); form.append("file", file);
const res = await fetch(`/api/rag/upload`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
if(res.ok) setUploaded(true);
setBusy(false);
};


const ask = async () => {
if(!question) return;
setAnswer(""); setBusy(true);
const token = await getAccessTokenSilently();
const res = await fetch(`/api/rag/ask`, {
method: "POST",
headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
body: JSON.stringify({ question })
});


// Stream response progressively
const reader = res.body.getReader();
const dec = new TextDecoder();
let partial = "";
while (true) {
const { done, value } = await reader.read();
if (done) break;
const lines = dec.decode(value).trim().split("\n");
for (let line of lines) {
try {
const j = JSON.parse(line);
if (j.response) {
partial += j.response;
setAnswer(partial);
}
} catch { continue; }
}
}
setBusy(false);
};


return (
<div className="page rag">
<h2>Chat with Document (RAG)</h2>
<div className="card">
<input type="file" accept=".txt,.pdf,.doc,.docx,.csv,.xls,.xlsx" onChange={e=>setFile(e.target.files[0])} />
<button onClick={upload} disabled={!file || busy}>{busy?"Uploading…":"Upload Document"}</button>
{uploaded && <span className="ok">✅ Uploaded</span>}
</div>
<p className="note">Supports TXT, PDF, DOC/DOCX, CSV, Excel (less than or equat to 20MB). Model can answer math from uploaded tables.</p>
<div className="card">
<input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about your document..." />
<button onClick={ask} disabled={!uploaded || busy}>{busy?"Thinking…":"Ask"}</button>
</div>
<div className="answer-stream">
<pre>{answer}</pre>
</div>
</div>
);
}
