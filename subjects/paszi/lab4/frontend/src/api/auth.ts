import { request } from "./client";

type Credentials = { login: string; password: string };

export type User = { id: number; login: string };

export function register(credentials: Credentials) {
    return request<{ message: string }>("/register", "POST", credentials);
}

export function login(credentials: Credentials) {
    return request<{ user: User }>("/login", "POST", credentials);
}

export function getCurrentUser() {
    return request<User>("/me");
}

export function logout() {
    return request<void>("/auth/logout", "POST");
}
