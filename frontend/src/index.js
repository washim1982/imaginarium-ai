import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Auth0Provider } from "@auth0/auth0-react";
import "./styles/index.css";
import App from "./App";

// Prefer build-time env. Fallback to window.__CONFIG__ injected at build (env.js) if missing.
const cfg = (typeof window !== "undefined" && window.__CONFIG__) || {};
const domain = process.env.REACT_APP_AUTH0_DOMAIN || cfg.AUTH0_DOMAIN;
const clientId = process.env.REACT_APP_AUTH0_CLIENT_ID || cfg.AUTH0_CLIENT_ID;
const audience = process.env.REACT_APP_AUTH0_AUDIENCE || cfg.AUTH0_AUDIENCE; // e.g. https://custom-ai-api

ReactDOM.createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      cacheLocation="localstorage"
      useRefreshTokens={true}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience,
        scope: "openid profile email",
      }}
    >
      <App />
    </Auth0Provider>
  </BrowserRouter>
);










// import React from "react";
// import ReactDOM from "react-dom/client";
// import { BrowserRouter, Routes, Route } from "react-router-dom";
// import { Auth0Provider } from "@auth0/auth0-react";
// import AppLayout from "./App";
// import ModelHub from "./pages/ModelHub";
// import Training from "./pages/Training";
// import SqlTrainer from "./pages/SqlTrainer";
// import Analysis from "./pages/Analysis";
// import OCR from "./pages/OCR";
// import Rag from "./pages/Rag";
// import Translation from "./pages/Translation";
// import "./App.css";

// const root = ReactDOM.createRoot(document.getElementById("root"));

// root.render(
//   <Auth0Provider
//     domain={process.env.REACT_APP_AUTH0_DOMAIN}
//     clientId={process.env.REACT_APP_AUTH0_CLIENT_ID}
//     authorizationParams={{
//       redirect_uri: window.location.origin,
//       audience: process.env.REACT_APP_AUTH0_AUDIENCE,
//     }}
//   >
//     <BrowserRouter>
//       <Routes>
//         <Route path="/" element={<AppLayout />}>
//           <Route index element={<ModelHub />} />
//           <Route path="models" element={<ModelHub />} />
//           <Route path="training" element={<Training />} />
//           <Route path="sql-trainer" element={<SqlTrainer />} />
//           <Route path="analysis" element={<Analysis />} />
//           <Route path="ocr" element={<OCR />} />
//           <Route path="rag" element={<Rag />} />
//           <Route path="translation" element={<Translation />} />
//         </Route>
//       </Routes>
//     </BrowserRouter>
//   </Auth0Provider>
// );
