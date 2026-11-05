import React, { FormEvent, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type User = { id: number; login: string };
type Rights = { can_read: boolean; can_update: boolean; can_delete: boolean };
type Resource = Rights & { id: number; title: string; owner_id: number; is_owner: boolean; content?: string };
type Grant = Rights & { login: string };
type Notice = { status: number; message: string; ok: boolean };
class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function api(path: string, method = 'GET', body?: unknown, token?: string) {
  let response: Response;
  try {
    response = await fetch('/api' + path, {
      method, headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch { throw new ApiError(0, 'Не удалось связаться с сервером. Повторите попытку.'); }
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, data.message || 'Не удалось выполнить действие');
  return { data, status: response.status };
}

function App() {
  const [mode, setMode] = useState(location.pathname === '/login' ? 'login' : 'register');
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState(''); // Сеанс хранится только в памяти этой вкладки.
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const [events, setEvents] = useState<Notice[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [id, setId] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [grants, setGrants] = useState<Grant[]>([]);
  const [target, setTarget] = useState('');
  const [rights, setRights] = useState<Rights>({ can_read: true, can_update: false, can_delete: false });
  const selected = resources.find(r => String(r.id) === id);

  function show(status: number, message: string) {
    const value = { status, message, ok: status >= 200 && status < 300 };
    setNotice(value);
    setEvents(old => [value, ...old].slice(0, 5));
  }
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setNotice(null);
    try { await action(); }
    catch (e) {
      if (e instanceof ApiError) {
        show(e.status, e.message);
        if (e.status === 401 && token) { setToken(''); setUser(null); }
      } else show(0, 'Не удалось выполнить действие. Повторите попытку.');
    } finally { setBusy(false); }
  }
  function changeMode(next: string) {
    setMode(next); setNotice(null);
    history.replaceState(null, '', '/' + next);
  }
  async function refresh(auth = token) {
    const { data } = await api('/resources', 'GET', undefined, auth);
    setResources(data);
  }
  async function loadGrants(resourceId: string) {
    const { data } = await api(`/resources/${resourceId}/permissions`, 'GET', undefined, token);
    setGrants(data);
  }
  useEffect(() => { setGrants([]); }, [id]);

  function authenticate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const values = new FormData(form);
    const credentials = { login: String(values.get('login')), password: String(values.get('password')) };
    void run(async () => {
      const { data, status } = await api(mode === 'register' ? '/register' : '/login', 'POST', credentials);
      form.reset();
      if (mode === 'register') show(status, data.message);
      else {
        setToken(data.access_token); setUser(data.user); setEvents([]); setNotice(null);
        history.replaceState(null, '', '/workspace');
        await refresh(data.access_token);
      }
    });
  }

  return <div className="shell">
    <aside className="sidebar">
      <a className="brand" href="/register"><span className="brand-mark">К</span>контур<span className="brand-dot">.</span></a>
      <div className="side-label">РАБОЧЕЕ ПРОСТРАНСТВО</div>
      <div className={'side-item ' + (!user ? 'active' : '')}><span>01</span> Учётная запись</div>
      <div className={'side-item ' + (user ? 'active' : '')}><span>02</span> Ресурсы и права</div>
      <div className="side-note"><div className="small-caps">ПРИНЦИП ДОСТУПА</div><p>Вы создаёте ресурс.<br />Вы решаете, кто может<br />с ним работать.</p><div className="rule-line" /><span>Дискреционная модель · DAC</span></div>
      <div className="side-footer">ИТМО · ПАСЗИ<br /><span>Лабораторная работа 04 / вариант 02</span></div>
    </aside>
    <main>
      <header><span>Управление доступом</span><div className="header-right"><span className="pill"><i />Учебный стенд</span>{user && <><strong>{user.login}</strong><button className="text-button" onClick={() => { setUser(null); setToken(''); setResources([]); setId(''); setTitle(''); setContent(''); setEvents([]); changeMode('login'); }}>Выйти</button></>}</div></header>
      <div className="page-content">
        <div className="eyebrow">ЛАБОРАТОРНАЯ 04 <span>/</span> ВАРИАНТ 02</div>
        <h1>{user ? 'Ваши ресурсы. Ваши правила.' : <>Доступ под вашим<br />контролем.</>}</h1>
        <p className="lead">{user ? 'Создавайте документы и выдавайте участникам только нужные права.' : 'Создайте учётную запись, чтобы работать с ресурсами и управлять правами участников.'}</p>
        {notice && <div className={'notice ' + (notice.ok ? 'success' : 'error')} role="status"><strong>{notice.status ? `HTTP ${notice.status}` : 'Ошибка сети'}</strong><span>{notice.message}</span></div>}
        {!user ? <div className="auth-grid">
          <section className="card auth-card">
            <div className="tabs"><button className={mode === 'register' ? 'chosen' : ''} onClick={() => changeMode('register')}>Регистрация</button><button className={mode === 'login' ? 'chosen' : ''} onClick={() => changeMode('login')}>Вход</button></div>
            <h2>{mode === 'register' ? 'Новая учётная запись' : 'С возвращением'}</h2>
            <p className="muted">{mode === 'register' ? 'Заполните два поля — и можно начинать.' : 'Введите логин и пароль вашей учётной записи.'}</p>
            <form onSubmit={authenticate} key={mode}>
              <label>Логин<input name="login" autoComplete="username" placeholder="Например, ivan.shibaev" required maxLength={32} /></label>
              <div className="hint">От 3 до 32 символов: латиница, цифры, точка, _ и -</div>
              <label>Пароль<input name="password" type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} placeholder="Введите пароль" required maxLength={128} /></label>
              <div className="hint">От 8 символов, заглавная и строчная латинские буквы, цифра и спецсимвол.</div>
              <button className="primary full" disabled={busy}>{busy ? 'Пожалуйста, подождите…' : mode === 'register' ? 'Создать учётную запись' : 'Войти в систему'}<span>↗</span></button>
            </form>
          </section>
          <section className="explanation"><div className="small-caps">КАК ЭТО РАБОТАЕТ</div><h2>Права начинаются<br />с владельца.</h2><p>У каждого ресурса есть владелец.<br />Остальные получают доступ только<br />после его разрешения.</p><div className="rights-example"><div><b>R</b><span>Читать</span></div><div><b>W</b><span>Изменять</span></div><div><b>D</b><span>Удалять</span></div></div><div className="explanation-foot">Каждое право назначается отдельно.<br />Владелец может отозвать его в любой момент.</div></section>
        </div> : <>
          <div className="workspace-grid">
            <section className="card resources-card"><div className="section-heading"><h2>Ресурсы</h2><span className="count">{resources.length}</span></div><p className="muted">Ваши объекты и выданные вам права.</p>
              <div className="resource-list">{resources.length ? resources.map(resource => <button className={'resource ' + (String(resource.id) === id ? 'selected' : '')} key={resource.id} onClick={() => { setId(String(resource.id)); setTitle(resource.title); setContent(''); if (resource.is_owner) void run(() => loadGrants(String(resource.id))); }}><span className="resource-top"><strong>{resource.title}</strong><span>#{resource.id}</span></span><span className="resource-bottom"><span>{resource.is_owner ? 'Вы — владелец' : 'Общий доступ'}</span><span className="right-tags">{resource.can_read && <b>R</b>}{resource.can_update && <b>W</b>}{resource.can_delete && <b>D</b>}</span></span></button>) : <div className="empty">Пока нет доступных ресурсов.<br />Создайте свой или попросите владельца выдать право.</div>}</div>
              <details className="create-panel"><summary>+ Создать ресурс</summary><form onSubmit={e => { e.preventDefault(); const form = e.currentTarget; const data = new FormData(form); void run(async () => { const result = await api('/resources', 'POST', { title: data.get('title'), content: data.get('content') }, token); await refresh(); setId(String(result.data.id)); setTitle(result.data.title); setContent(result.data.content); setGrants([]); form.reset(); show(result.status, `Ресурс #${result.data.id} создан`); }); }}><label>Название нового ресурса<input name="title" required maxLength={100} /></label><label>Содержимое нового ресурса<textarea name="content" required maxLength={10000} rows={3} /></label><button className="primary full" disabled={busy}>Создать ресурс</button></form></details>
            </section>
            <section className="card document-card"><div className="section-heading"><h2>Работа с ресурсом</h2><span className="small-caps">R / W / D</span></div><p className="muted">Выберите объект слева или введите его номер.</p><label>Номер ресурса<input type="number" min="1" value={id} onChange={e => { setId(e.target.value); setTitle(''); setContent(''); }} placeholder="Введите ID" /></label>
              <label>Название<input value={title} onChange={e => setTitle(e.target.value)} maxLength={100} /></label><label>Содержимое<textarea value={content} onChange={e => setContent(e.target.value)} maxLength={10000} rows={4} placeholder="Нажмите «Прочитать», чтобы загрузить содержимое" /></label>
              <div className="actions"><button className="primary" disabled={busy || !id} onClick={() => void run(async () => { const { data, status } = await api(`/resources/${id}`, 'GET', undefined, token); setTitle(data.title); setContent(data.content); show(status, `Чтение ресурса #${id} разрешено`); })}>Прочитать</button><button className="secondary" disabled={busy || !id} onClick={() => void run(async () => { const { status } = await api(`/resources/${id}`, 'PATCH', { title, content }, token); await refresh(); show(status, `Ресурс #${id} изменён`); })}>Сохранить</button><button className="danger" disabled={busy || !id} onClick={() => { if (confirm(`Удалить ресурс #${id}?`)) void run(async () => { const { status } = await api(`/resources/${id}`, 'DELETE', undefined, token); await refresh(); setId(''); setTitle(''); setContent(''); show(status, 'Ресурс удалён'); }); }}>Удалить</button></div>
              <div className="hint">Для каждого действия проверяется отдельное право доступа.</div>
            </section>
          </div>
          {selected?.is_owner && <section className="card permission-card"><div><div className="eyebrow">ВЫ — ВЛАДЕЛЕЦ</div><h2>Управление правами <span className="muted">#{id}</span></h2><p className="muted">Выберите участника и разрешённые действия.</p></div><form className="permission-form" onSubmit={e => { e.preventDefault(); void run(async () => { const { status } = await api(`/resources/${id}/permissions/${encodeURIComponent(target)}`, 'PUT', rights, token); await loadGrants(id); show(status, `Права пользователя ${target} сохранены`); }); }}><label>Логин участника<input value={target} onChange={e => setTarget(e.target.value)} placeholder="Логин зарегистрированного пользователя" required /></label><div className="checkboxes">{([['can_read', 'Чтение'], ['can_update', 'Изменение'], ['can_delete', 'Удаление']] as const).map(([key, label]) => <label key={key}><input type="checkbox" checked={rights[key]} onChange={e => setRights({ ...rights, [key]: e.target.checked })} />{label}</label>)}</div><button className="primary" disabled={busy}>Сохранить права</button></form>{grants.length > 0 && <div className="grant-list">{grants.map(g => <div className="grant" key={g.login}><strong>{g.login}</strong><span>{[g.can_read && 'Чтение', g.can_update && 'Изменение', g.can_delete && 'Удаление'].filter(Boolean).join(' · ') || 'Все действия запрещены'}</span><button className="text-button" disabled={busy} onClick={() => void run(async () => { const { status } = await api(`/resources/${id}/permissions/${encodeURIComponent(g.login)}`, 'DELETE', undefined, token); await loadGrants(id); show(status, `Права пользователя ${g.login} отозваны`); })}>Отозвать</button></div>)}</div>}</section>}
          {events.length > 0 && <section className="activity"><h3>Последние действия</h3>{events.map((item, i) => <div key={i}><span className={item.ok ? 'code good' : 'code bad'}>{item.status || 'Сеть'}</span><span>{item.message}</span></div>)}</section>}
        </>}
        <footer>ПАСЗИ · Регистрация пользователя и модели разграничения доступа <span>04 / DAC</span></footer>
      </div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
