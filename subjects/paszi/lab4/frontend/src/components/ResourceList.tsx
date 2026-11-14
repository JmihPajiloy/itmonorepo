import type { FormEvent } from "react";
import type { Resource, ResourceInput } from "../api/resources";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";

type ResourceListProps = {
    resources: Resource[];
    selectedId: string;
    busy: boolean;
    onSelect: (resource: Resource) => void;
    onCreate: (fields: ResourceInput) => Promise<boolean>;
};

export function ResourceList({ resources, selectedId, busy, onSelect, onCreate }: ResourceListProps) {
    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const form = event.currentTarget;
        const fields = new FormData(form);
        if (await onCreate({
            title: String(fields.get("title")),
            content: String(fields.get("content")),
        })) {
            form.reset();
        }
    }

    return (
        <Card className="resources-card">
            <h2>Ресурсы <span className="count">{resources.length}</span></h2>
            <div className="resource-list">
                {resources.length === 0 && <p className="muted">Пока нет доступных ресурсов.</p>}
                {resources.map(resource => (
                    <Button
                        key={resource.id}
                        variant="plain"
                        className="resource"
                        aria-pressed={String(resource.id) === selectedId}
                        disabled={busy}
                        onClick={() => onSelect(resource)}
                    >
                        <span className="resource-top">
                            <strong>{resource.title}</strong>
                            <span>#{resource.id}</span>
                        </span>
                        <span className="resource-bottom">
                            <span>{resource.is_owner ? "Вы — владелец" : "Общий доступ"}</span>
                            <span className="right-tags">
                                {resource.can_read && <b title="Чтение">R</b>}
                                {resource.can_update && <b title="Изменение">W</b>}
                                {resource.can_delete && <b title="Удаление">D</b>}
                            </span>
                        </span>
                    </Button>
                ))}
            </div>
            <details className="create-panel">
                <summary>+ Создать ресурс</summary>
                <form onSubmit={submit}>
                    <label>
                        Название нового ресурса
                        <Input name="title" maxLength={100} required />
                    </label>
                    <label>
                        Содержимое нового ресурса
                        <Textarea name="content" rows={3} maxLength={10000} required />
                    </label>
                    <Button type="submit" disabled={busy}>Создать ресурс</Button>
                </form>
            </details>
        </Card>
    );
}
