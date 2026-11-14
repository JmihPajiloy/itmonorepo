import { useState, type FormEvent } from "react";
import type { Grant, Rights } from "../api/resources";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";

const permissions = [
    ["can_read", "Чтение"],
    ["can_update", "Изменение"],
    ["can_delete", "Удаление"],
] as const;

type PermissionsProps = {
    id: string;
    grants: Grant[];
    busy: boolean;
    onSave: (login: string, rights: Rights) => void;
    onRevoke: (login: string) => void;
};

export function Permissions({ id, grants, busy, onSave, onRevoke }: PermissionsProps) {
    const [login, setLogin] = useState("");
    const [rights, setRights] = useState<Rights>({ can_read: true, can_update: false, can_delete: false });

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        onSave(login, rights);
    }

    return (
        <Card className="permission-card">
            <h2>Управление правами <span className="muted">#{id}</span></h2>
            <form className="permission-form" onSubmit={submit}>
                <label>
                    Логин участника
                    <Input value={login} onChange={event => setLogin(event.target.value)} required />
                </label>
                <div className="checkboxes">
                    {permissions.map(([key, label]) => (
                        <label key={key}>
                            <Input
                                type="checkbox"
                                checked={rights[key]}
                                onChange={event => setRights({ ...rights, [key]: event.target.checked })}
                            />
                            {label}
                        </label>
                    ))}
                </div>
                <Button type="submit" disabled={busy}>Сохранить права</Button>
            </form>
            {grants.length > 0 && (
                <div className="grant-list">
                    {grants.map(grant => (
                        <div className="grant" key={grant.login}>
                            <strong>{grant.login}</strong>
                            <span>{permissions.filter(([key]) => grant[key]).map(([, label]) => label).join(" · ") || "Все действия запрещены"}</span>
                            <Button variant="link" disabled={busy} onClick={() => onRevoke(grant.login)}>Отозвать</Button>
                        </div>
                    ))}
                </div>
            )}
        </Card>
    );
}
