import React from "react";
import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import { useNavigate } from "react-router-dom";


export function Auth0ProviderWithNavigate({ children }) {
const navigate = useNavigate();
const domain = process.env.REACT_APP_AUTH0_DOMAIN;
const clientId = process.env.REACT_APP_AUTH0_CLIENT_ID;
const audience = process.env.REACT_APP_AUTH0_AUDIENCE;
const onRedirectCallback = (appState) => navigate(appState?.returnTo || window.location.pathname);
return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: process.env.REACT_APP_AUTH0_AUDIENCE, // ✅ this line ensures you get an access token for the API
        scope: "openid profile email",
      }}
      onRedirectCallback={onRedirectCallback}
      cacheLocation="localstorage" // keeps token after reloads
      useRefreshTokens={true}       // automatically refreshes expired tokens
    >
      {children}
    </Auth0Provider>
  );
}


export function RequireAuth({ children }) {
    const { isAuthenticated, loginWithRedirect } = useAuth0();
    if (!isAuthenticated) { loginWithRedirect(); return null; }
    return children;
}