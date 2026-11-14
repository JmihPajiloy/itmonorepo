import type { ResourceInput } from "../api/resources";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";

type ResourceEditorProps = {
    id: string;
    fields: ResourceInput;
    busy: boolean;
    onIdChange: (id: string) => void;
    onFieldsChange: (fields: ResourceInput) => void;
    onRead: () => void;
    onUpdate: () => void;
    onDelete: () => void;
};

export function ResourceEditor({
    id, fields, busy, onIdChange, onFieldsChange, onRead, onUpdate, onDelete,
}: ResourceEditorProps) {
    return (
        <Card className="document-card">
            <h2>Работа с ресурсом</h2>
            <p className="muted">Выберите ресурс из списка или введите его номер.</p>
            <label>
                Номер ресурса
                <Input type="number" min="1" value={id} disabled={busy} onChange={event => onIdChange(event.target.value)} />
            </label>
            <label>
                Название
                <Input value={fields.title} maxLength={100} onChange={event => onFieldsChange({ ...fields, title: event.target.value })} />
            </label>
            <label>
                Содержимое
                <Textarea
                    value={fields.content}
                    onChange={event => onFieldsChange({ ...fields, content: event.target.value })}
                    maxLength={10000}
                    rows={4}
                />
            </label>
            <div className="actions">
                <Button disabled={busy || !id} onClick={onRead}>Прочитать</Button>
                <Button variant="secondary" disabled={busy || !id} onClick={onUpdate}>Сохранить</Button>
                <Button variant="destructive" disabled={busy || !id} onClick={onDelete}>Удалить</Button>
            </div>
        </Card>
    );
}
