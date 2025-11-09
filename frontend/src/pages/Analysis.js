import React, { useState } from "react";
import { useApi } from "../services/api";
import "../styles/page-analysis.css";


export default function Analysis(){
const api = useApi();
const [file, setFile] = useState(null);
const [preview, setPreview] = useState([]);
const [cols, setCols] = useState([]);
const [x, setX] = useState("");
const [y, setY] = useState("");
const [chartUrl, setChartUrl] = useState(null);


const upload = async () => {
if(!file) return;
const form = new FormData();
form.append("file", file);
const { data } = await api.post("/analysis/upload", form, { headers: {"Content-Type":"multipart/form-data"}});
setPreview(data.preview || []);
setCols(data.columns || []);
setX(data.columns?.[0] || "");
setY(data.columns?.[1] || "");
};


const gen = async () => {
if(!x || !y) return;
const res = await api.get(`/analysis/chart`, { responseType: "blob", params: { x, y } });
const url = URL.createObjectURL(res.data);
setChartUrl(url);
};


return (
<div className="page analysis">
<h2>File Analytics</h2>
<div className="card">
<input type="file" accept=".csv,.xlsx" onChange={e=>setFile(e.target.files[0])} />
<button onClick={upload}>Upload & Preview</button>
</div>
{preview.length>0 && (
<>
<div className="table-scroll">
<table>
<thead>
<tr>{Object.keys(preview[0]||{}).map(h=> <th key={h}>{h}</th>)}</tr>
</thead>
<tbody>
{preview.map((row,i)=>(
<tr key={i}>{Object.values(row).map((v,j)=><td key={j}>{String(v)}</td>)}</tr>
))}
</tbody>
</table>
</div>
<div className="controls">
<label>X</label>
<select value={x} onChange={e=>setX(e.target.value)}>{cols.map(c=> <option key={c}>{c}</option>)}</select>
<label>Y</label>
<select value={y} onChange={e=>setY(e.target.value)}>{cols.map(c=> <option key={c}>{c}</option>)}</select>
<button onClick={gen}>Generate Chart</button>
</div>
{chartUrl && <img className="chart" alt="Bar chart" src={chartUrl} />}
</>
)}
</div>
);
}