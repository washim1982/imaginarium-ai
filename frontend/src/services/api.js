import axios from "axios";
import { useAuth0 } from "@auth0/auth0-react";

export function useApi() {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const audience = process.env.REACT_APP_AUTH0_AUDIENCE;

  const api = axios.create({ baseURL: "/api" }); // ✅ consistent for all routes

  api.interceptors.request.use(async (config) => {
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: { audience, scope: "openid profile email" },
      });
      config.headers.Authorization = `Bearer ${token}`;
    } catch (e) {
      const needConsent =
        e?.error === "consent_required" ||
        e?.error === "login_required" ||
        String(e?.message || "").toLowerCase().includes("consent required");
      if (needConsent) {
        await loginWithRedirect({
          authorizationParams: {
            prompt: "consent",
            audience,
            scope: "openid profile email",
          },
        });
      }
    }
    return config;
  });

  api.interceptors.response.use(
    (r) => r,
    async (err) => {
      if (err?.response?.status === 401) {
        await loginWithRedirect({
          authorizationParams: {
            prompt: "login",
            audience,
            scope: "openid profile email",
          },
        });
      }
      throw err;
    }
  );

  return api;
}
