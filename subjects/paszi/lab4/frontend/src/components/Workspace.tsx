import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import {
    createResource,
    deleteResource,
    listGrants,
    listResources,
    readResource,
    revokeGrant,
    saveGrant,
    updateResource,
    type Grant,
    type Resource,
    type ResourceInput,
    type Rights,
} from "../api/resources";
import { Notice, type NoticeValue } from "./Notice";
import { Permissions } from "./Permissions";
import { ResourceEditor } from "./ResourceEditor";
import { ResourceList } from "./ResourceList";

const emptyFields: ResourceInput = { title: "", content: "" };

export function Workspace({ onSessionExpired }: { onSessionExpired: (error: ApiError) => void }) {
    const [notice, setNotice] = useState<NoticeValue | null>(null);
    const [events, setEvents] = useState<NoticeValue[]>([]);
    const [busy, setBusy] = useState(false);
    const [loading, setLoading] = useState(true);
    const [resources, setResources] = useState<Resource[]>([]);
    const [id, setId] = useState("");
    const [fields, setFields] = useState(emptyFields);
    const [grants, setGrants] = useState<Grant[]>([]);
    const [loadingGrants, setLoadingGrants] = useState(false);
    const owned = resources.some(resource => String(resource.id) === id && resource.is_owner);

    const show = useCallback((status: number, message: string) => {
        const value = { status, message, ok: status >= 200 && status < 300 };
        setNotice(value);
        setEvents(previous => [value, ...previous].slice(0, 5));
    }, []);

    const showError = useCallback((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
            onSessionExpired(error);
            return;
        }
        show(error instanceof ApiError ? error.status : 0,
            error instanceof ApiError ? error.message : "Не удалось выполнить действие. Повторите попытку.");
    }, [onSessionExpired, show]);

    useEffect(() => {
        let active = true;
        void listResources()
            .then(({ data }) => { if (active) setResources(data); })
            .catch(error => { if (active) showError(error); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [showError]);

    useEffect(() => {
        if (!owned) return;
        let active = true;
        setLoadingGrants(true);
        void listGrants(id)
            .then(({ data }) => { if (active) setGrants(data); })
            .catch(error => { if (active) showError(error); })
            .finally(() => { if (active) setLoadingGrants(false); });
        return () => { active = false; };
    }, [id, owned, showError]);

    async function run(action: () => Promise<void>) {
        setBusy(true);
        setNotice(null);
        try {
            await action();
            return true;
        } catch (error) {
            showError(error);
            return false;
        } finally {
            setBusy(false);
        }
    }

    async function refreshResources() {
        setResources((await listResources()).data);
    }

    async function refreshGrants(resourceId: string) {
        setGrants((await listGrants(resourceId)).data);
    }

    function select(resourceId: string, nextFields = emptyFields) {
        setId(resourceId);
        setFields(nextFields);
        setGrants([]);
    }

    function selectResource(resource: Resource) {
        if (String(resource.id) !== id) {
            select(String(resource.id), { title: resource.title, content: "" });
        }
    }

    function create(fields: ResourceInput) {
        return run(async () => {
            const { data, status } = await createResource(fields);
            await refreshResources();
            select(String(data.id), { title: data.title, content: data.content });
            show(status, `Ресурс #${data.id} создан`);
        });
    }

    function read() {
        void run(async () => {
            const { data, status } = await readResource(id);
            setFields({ title: data.title, content: data.content });
            show(status, `Чтение ресурса #${id} разрешено`);
        });
    }

    function update() {
        void run(async () => {
            const { status } = await updateResource(id, fields);
            await refreshResources();
            show(status, `Ресурс #${id} изменён`);
        });
    }

    function remove() {
        if (!window.confirm(`Удалить ресурс #${id}?`)) return;
        void run(async () => {
            const { status } = await deleteResource(id);
            await refreshResources();
            select("");
            show(status, "Ресурс удалён");
        });
    }

    function grant(login: string, rights: Rights) {
        void run(async () => {
            const { status } = await saveGrant(id, login, rights);
            await refreshGrants(id);
            show(status, `Права пользователя ${login} сохранены`);
        });
    }

    function revoke(login: string) {
        void run(async () => {
            const { status } = await revokeGrant(id, login);
            await refreshGrants(id);
            show(status, `Права пользователя ${login} отозваны`);
        });
    }

    return (
        <>
            <h1>Ресурсы и права</h1>
            {notice && <Notice value={notice} />}
            <div className="workspace-grid">
                <ResourceList resources={resources} selectedId={id} busy={busy || loading} onSelect={selectResource} onCreate={create} />
                <ResourceEditor
                    id={id}
                    fields={fields}
                    busy={busy || loading}
                    onIdChange={select}
                    onFieldsChange={setFields}
                    onRead={read}
                    onUpdate={update}
                    onDelete={remove}
                />
            </div>
            {owned && <Permissions key={id} id={id} grants={grants} busy={busy || loadingGrants} onSave={grant} onRevoke={revoke} />}
            {events.length > 0 && (
                <section className="activity">
                    <h2>Последние действия</h2>
                    <ul>
                        {events.map((event, index) => (
                            <li key={index}>
                                <span className={event.ok ? "good" : "bad"}>{event.status || "Сеть"}</span> {event.message}
                            </li>
                        ))}
                    </ul>
                </section>
            )}
        </>
    );
}
