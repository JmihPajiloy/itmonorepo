import { request } from "./client";

export type Rights = {
    can_read: boolean;
    can_update: boolean;
    can_delete: boolean;
};
export type Resource = Rights & {
    id: number;
    title: string;
    owner_id: number;
    is_owner: boolean;
};
export type ResourceInput = { title: string; content: string };
export type Document = Resource & ResourceInput;
export type Grant = Rights & { login: string };

export function listResources() {
    return request<Resource[]>("/resources", "GET");
}

export function createResource(fields: ResourceInput) {
    return request<Document>("/resources", "POST", fields);
}

export function readResource(id: string) {
    return request<Document>(`/resources/${encodeURIComponent(id)}`, "GET");
}

export function updateResource(id: string, fields: ResourceInput) {
    return request<{ id: number; message: string }>(`/resources/${encodeURIComponent(id)}`, "PATCH", fields);
}

export function deleteResource(id: string) {
    return request<void>(`/resources/${encodeURIComponent(id)}`, "DELETE");
}

export function listGrants(id: string) {
    return request<Grant[]>(`/resources/${encodeURIComponent(id)}/permissions`, "GET");
}

function grantPath(id: string, login: string) {
    return `/resources/${encodeURIComponent(id)}/permissions/${encodeURIComponent(login)}`;
}

export function saveGrant(id: string, login: string, rights: Rights) {
    return request<Grant>(grantPath(id, login), "PUT", rights);
}

export function revokeGrant(id: string, login: string) {
    return request<void>(grantPath(id, login), "DELETE");
}
