export class ApiError extends Error {
    constructor(
        public status: number,
        message: string,
    ) {
        super(message);
    }
}

async function send<T>(
    path: string,
    method = "GET",
    body?: unknown,
) {
    let response: Response;
    try {
        response = await fetch("/api" + path, {
            method,
            credentials: "same-origin",
            headers: {
                ...(body ? { "Content-Type": "application/json" } : {}),
            },
            ...(body ? { body: JSON.stringify(body) } : {}),
        });
    } catch {
        throw new ApiError(0, "Не удалось связаться с сервером. Повторите попытку.");
    }

    const data = response.status === 204 ? undefined : await response.json().catch(() => undefined);
    if (!response.ok) {
        throw new ApiError(response.status, data?.message || "Не удалось выполнить действие");
    }
    return { data: data as T, status: response.status };
}

let refreshInFlight: Promise<unknown> | undefined;

export async function request<T>(path: string, method = "GET", body?: unknown) {
    try {
        return await send<T>(path, method, body);
    } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401
            || path === "/login" || path === "/register" || path.startsWith("/auth/")) {
            throw error;
        }

        refreshInFlight ??= send<void>("/auth/refresh", "POST").finally(() => {
            refreshInFlight = undefined;
        });
        await refreshInFlight;
        return send<T>(path, method, body);
    }
}
