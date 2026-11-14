export type NoticeValue = { status: number; message: string; ok: boolean };

export function Notice({ value }: { value: NoticeValue }) {
    return (
        <div className={value.ok ? "notice success" : "notice error"} role="status">
            <strong>{value.status ? `HTTP ${value.status}` : "Ошибка сети"}</strong>
            <span>{value.message}</span>
        </div>
    );
}
