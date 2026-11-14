import { useState, type FormEvent } from "react";
import { NavLink, useLocation, useNavigate } from "react-router";
import { login, register } from "../api/auth";
import { ApiError } from "../api/client";
import { Notice, type NoticeValue } from "./Notice";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";

type AuthPageProps = {
    mode: "register" | "login";
};

export function AuthPage({ mode }: AuthPageProps) {
    const registering = mode === "register";
    const { state } = useLocation();
    const navigate = useNavigate();
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState<NoticeValue | null>(
        registering && typeof state?.error?.status === "number" && typeof state.error.message === "string"
            ? { status: state.error.status, message: state.error.message, ok: false }
            : null,
    );

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const form = event.currentTarget;
        const values = new FormData(form);
        const credentials = {
            login: String(values.get("login")),
            password: String(values.get("password")),
        };

        setBusy(true);
        setNotice(null);
        try {
            if (registering) {
                const { data, status } = await register(credentials);
                form.reset();
                setNotice({ status, message: data.message, ok: true });
            } else {
                await login(credentials);
                void navigate(state?.from ?? "/workspace", { replace: true });
            }
        } catch (error) {
            setNotice({
                status: error instanceof ApiError ? error.status : 0,
                message: error instanceof ApiError ? error.message : "Не удалось выполнить действие.",
                ok: false,
            });
        } finally {
            setBusy(false);
        }
    }

    return (
        <>
            <h1>{registering ? "Регистрация" : "Вход"}</h1>
            {notice && <Notice value={notice} />}
            <div className="auth-grid">
                <Card className="auth-card">
                    <nav className="tabs" aria-label="Учётная запись">
                        <Button variant="plain" asChild>
                            <NavLink to="/register" state={{ from: state?.from }}>Регистрация</NavLink>
                        </Button>
                        <Button variant="plain" asChild>
                            <NavLink to="/login" state={{ from: state?.from }}>Вход</NavLink>
                        </Button>
                    </nav>
                    <form onSubmit={submit}>
                        <label>
                            Логин
                            <Input name="login" autoComplete="username" required maxLength={32} />
                        </label>
                        {registering && <div className="hint">От 3 до 32 символов: латиница, цифры, точка, _ и -</div>}
                        <label>
                            Пароль
                            <Input
                                name="password"
                                type="password"
                                autoComplete={registering ? "new-password" : "current-password"}
                                required
                                maxLength={128}
                            />
                        </label>
                        {registering && (
                            <div className="hint">От 8 символов, заглавная и строчная латинские буквы, цифра и спецсимвол.</div>
                        )}
                        <Button className="full" type="submit" disabled={busy}>
                            {registering ? "Создать учётную запись" : "Войти в систему"}
                        </Button>
                    </form>
                </Card>
            </div>
        </>
    );
}
