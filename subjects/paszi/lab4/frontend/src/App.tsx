import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { AuthPage } from "./components/AuthPage";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import { Workspace } from "./components/Workspace";

export function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Navigate to="/register" replace />} />
                <Route path="/register" element={<Layout><AuthPage key="register" mode="register" /></Layout>} />
                <Route path="/login" element={<Layout><AuthPage key="login" mode="login" /></Layout>} />
                <Route
                    path="/workspace"
                    element={
                        <RequireAuth>
                            {reject => <Workspace onSessionExpired={reject} />}
                        </RequireAuth>
                    }
                />
                <Route path="*" element={<Navigate to="/register" replace />} />
            </Routes>
        </BrowserRouter>
    );
}
