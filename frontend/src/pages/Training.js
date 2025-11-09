import React, { useEffect, useState } from "react";
import { useApi } from "../services/api";
import "../styles/page-training.css";


export default function Training(){
const api = useApi();
const [models, setModels] = useState([]);
const [base, setBase] = useState("granite4:tiny-h");
const [newName, setNewName] = useState("");
const [file, setFile] = useState(null);
const [result, setResult] = useState(null);
const [busy, setBusy] = useState(false);


useEffect(()=>{ (async()=>{
const { data } = await api.get("/models");
setModels(data.models || []);
})(); }, [api]);


const start = async () => {
if(!newName) return;
setBusy(true); setResult(null);
// Simulated training — backend ignores file for now, but we keep the UI flow.
const { data } = await api.post("/training/lora", { base_model: base, new_model: newName });
setResult(data.model);
setBusy(false);
};


return (
<div className="page training">
<h2>Custom Model Training</h2>
<div className="card">
<label>Base model</label>
<select value={base} onChange={e=>setBase(e.target.value)}>
{models.map(m => <option key={m} value={m}>{m}</option>)}
</select>
<label>New model name</label>
<input value={newName} onChange={e=>setNewName(e.target.value)} placeholder="my-model-name" />
<label>Training data (optional)</label>
<input type="file" onChange={e=>setFile(e.target.files[0])} />
<button onClick={start} disabled={busy || !newName}>{busy?"Training…":"Start Training"}</button>
</div>
{result && <div className="result">Created: <code>{result}</code></div>}
</div>
);
}
