import React from "react";
import { useAuth0 } from "@auth0/auth0-react";


export default function Header(){
    const { isAuthenticated, loginWithRedirect, logout, user } = useAuth0();
    return (
        <header className="header">
        <h2>Imaginarium AI</h2>
            <nav>
            {!isAuthenticated ? (
            <button onClick={() => loginWithRedirect()}>Login</button>
            ) : (
            <>
                <span>{user?.email}</span>
                <button onClick={() => logout({ logoutParams: { returnTo: window.location.origin }})}>Logout</button>
            </>
            )}
            </nav>
        </header>
    );
}