import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { getCurrentUser, logout, type User } from "../api/auth";
import { ApiError } from "../api/client";
import { Layout } from "./Layout";
import { Notice, type NoticeValue } from "./Notice";

type AuthState =
    | { key: string; user: User }
    | { key: string; error: ApiError };

export function RequireAuth({ children }: { children: (reject: (error: ApiError) => void) => ReactNode }) {
    const { key, pathname, search, hash } = useLocation();
    const [auth, setAuth] = useState<AuthState | null>(null);
    const [signedOut, setSignedOut] = useState(false);
    const [logoutError, setLogoutError] = useState<NoticeValue | null>(null);

    const reject = useCallback((error: ApiError) => setAuth({ key, error }), [key]);

    useEffect(() => {
        let active = true;
        void getCurrentUser()
            .then(({ data }) => {
                if (active) setAuth({ key, user: data });
            })
            .catch((error: ApiError) => {
                if (active) reject(error);
            });
        return () => { active = false; };
    }, [key, reject]);

    async function signOut() {
        setLogoutError(null);
        try {
            await logout();
            setSignedOut(true);
        } catch (error) {
            if (error instanceof ApiError) {
                setLogoutError({ status: error.status, message: error.message, ok: false });
            }
        }
    }

    if (signedOut) return <Navigate to="/register" replace />;

    if (auth?.key !== key) {
        return <Layout><p role="status">Проверяем сеанс…</p></Layout>;
    }

    if ("error" in auth) {
        const { status, message } = auth.error;
        if (status === 401) {
            return <Navigate to="/register" replace state={{ from: { pathname, search, hash }, error: { status, message } }} />;
        }
        return <Layout><Notice value={{ status, message, ok: false }} /></Layout>;
    }

    return (
        <Layout login={auth.user.login} onLogout={signOut}>
            {logoutError && <Notice value={logoutError} />}
            {children(reject)}
        </Layout>
    );
}
