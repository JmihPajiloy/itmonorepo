import type { PropsWithChildren } from "react";
import { Link } from "react-router";
import { Button } from "./ui/button";

type LayoutProps = PropsWithChildren<{ login?: string; onLogout?: () => void }>;

export function Layout({ login, onLogout, children }: LayoutProps) {
    return (
        <div className="shell">
            <aside className="sidebar">
                <Link className="brand" to={login ? "/workspace" : "/register"}>
                    <span className="brand-mark">К</span>контур.
                </Link>
                <div className="side-item">{login ? "Ресурсы и права" : "Учётная запись"}</div>
                <div className="side-footer">ИТМО · ПАСЗИ<br />Лабораторная работа № 4 · Вариант 2</div>
            </aside>
            <main>
                <header>
                    <span>Управление доступом</span>
                    {login && (
                        <div className="header-right">
                            <strong>{login}</strong>
                            <Button variant="link" onClick={onLogout}>Выйти</Button>
                        </div>
                    )}
                </header>
                <div className="page-content">{children}</div>
            </main>
        </div>
    );
}
