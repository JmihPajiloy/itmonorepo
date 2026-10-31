import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {readFileSync, existsSync} from "node:fs";
import vm from "node:vm";

const web = new URL("web/", import.meta.url);
const pages = ["index.html", "page2.html", "page3.html"];
for (const [index, page] of pages.entries()) {
  const html = readFileSync(new URL(page, web), "utf8");
  for (const required of ['lang="ru"', 'id="mode"', 'id="toggle"', 'src="protect.js"', 'href="style.css"', '<img ', '<main>']) {
    assert.ok(html.includes(required), `${page}: отсутствует ${required}`);
  }
  for (const [, resource] of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
    assert.ok(existsSync(new URL(resource, web)), `${page}: нет ресурса ${resource}`);
  }
  if (index < 2) assert.ok(html.includes(`href="${pages[index + 1]}"`));
}

const source = readFileSync(new URL("protect.js", web), "utf8");
function loadPage(storage = new Map()) {
  const listeners = new Map();
  const classes = new Set();
  const button = {textContent: "", disabled: true, addEventListener: (_type, callback) => {button.click = callback;}};
  const mode = {textContent: ""};
  const alerts = [];
  const context = vm.createContext({
    atob, crypto: webcrypto, TextDecoder, TextEncoder,
    prompt: () => context.password,
    alert: message => alerts.push(message),
    window: {addEventListener: (name, callback) => listeners.set(`window:${name}`, callback)},
    document: {
      addEventListener: (name, callback) => listeners.set(name, callback),
      documentElement: {classList: {
        add: name => classes.add(name),
        remove: name => classes.delete(name),
        toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
      }},
      getElementById: id => id === "toggle" ? button : mode,
    },
    sessionStorage: {
      getItem: key => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => storage.delete(key),
    },
  });
  vm.runInContext(source, context);
  listeners.get("DOMContentLoaded")();
  return {
    classes, button, mode, context, alerts,
    event(type, properties = {}) {
      let prevented = false;
      listeners.get(type)({...properties, preventDefault: () => {prevented = true;}});
      return prevented;
    },
  };
}

// A previous storage key must not bypass the current password verifier.
const storage = new Map([["timp-copy-unlocked", "yes"]]);
const page = loadPage(storage);
assert.equal(page.classes.has("protected"), true);
assert.equal(page.button.disabled, false);
assert.equal(await vm.runInContext('validPassword("admin")', page.context), true);
assert.equal(await vm.runInContext('validPassword("wrong")', page.context), false);
for (const type of ["copy", "cut", "contextmenu", "dragstart", "selectstart"]) {
  assert.equal(page.event(type), true, `${type}: защита включена`);
}
for (const key of ["c", "x", "s", "a", "u"]) {
  assert.equal(page.event("keydown", {ctrlKey: true, key}), true);
  assert.equal(page.event("keydown", {metaKey: true, key: key.toUpperCase()}), true);
}
assert.equal(page.event("keydown", {metaKey: true, key: "p"}), false, "Печать разрешена");
assert.equal(page.event("keydown", {ctrlKey: true, key: "p"}), false);
assert.equal(page.event("keydown", {key: "Tab"}), false, "Навигация доступна");
for (const first of ["Meta", "Shift"]) {
  page.event("keydown", {key: first, metaKey: first === "Meta", shiftKey: first === "Shift"});
  assert.equal(page.classes.has("screenshot-blur"), false, "Один модификатор не размывает страницу");
  page.event("keydown", {key: first === "Meta" ? "Shift" : "Meta", metaKey: true, shiftKey: true});
  assert.equal(page.classes.has("screenshot-blur"), true, "Оба порядка нажатия включают размытие");
  page.event("keydown", {key: "K", metaKey: true, shiftKey: true});
  page.event("keyup", {key: "K", metaKey: true, shiftKey: true});
  assert.equal(page.classes.has("screenshot-blur"), true, "Другие клавиши не снимают размытие");
  page.event("keyup", {key: first, metaKey: first !== "Meta", shiftKey: first !== "Shift"});
  assert.equal(page.classes.has("screenshot-blur"), false, "Отпускание любого модификатора снимает размытие");
  page.event("keyup", {key: first === "Meta" ? "Shift" : "Meta", metaKey: false, shiftKey: false});
}
for (const type of ["window:blur", "window:focus", "visibilitychange"]) {
  page.event("keydown", {key: "Shift", metaKey: true, shiftKey: true});
  page.context.document.hidden = type === "visibilitychange";
  page.event(type);
  assert.equal(page.classes.has("screenshot-blur"), false, "Размытие не залипает при смене окна или вкладки");
}
page.context.document.hidden = false;

page.context.password = null;
await page.button.click();
assert.equal(page.classes.has("protected"), true);
page.context.password = "wrong";
await page.button.click();
assert.equal(page.classes.has("protected"), true);
assert.equal(page.alerts.at(-1), "Неверный пароль");
page.context.password = "admin";
page.event("keydown", {key: "Shift", metaKey: true, shiftKey: true});
await page.button.click();
assert.equal(page.classes.has("protected"), false);
assert.equal(page.classes.has("screenshot-blur"), false);
assert.equal(page.mode.textContent, "Копирование разрешено");
for (const type of ["copy", "cut", "contextmenu", "dragstart", "selectstart"]) {
  assert.equal(page.event(type), false, `${type}: защита отключена`);
}
assert.equal(page.event("keydown", {ctrlKey: true, key: "s"}), false);
assert.equal(page.event("keydown", {metaKey: true, shiftKey: true, code: "Digit4", key: "4"}), false);
assert.equal(page.classes.has("screenshot-blur"), false, "При отключённой защите размытия нет");
const next = loadPage(storage);
assert.equal(next.classes.has("protected"), false, "Режим сохраняется при переходе");
await next.button.click();
assert.equal(next.classes.has("protected"), true);
assert.equal(next.event("copy"), true);
assert.equal(loadPage(storage).classes.has("protected"), true);
assert.equal(loadPage().classes.has("protected"), true, "Новая сессия защищена");
console.log("Веб-проверка: страницы, пароль, копирование, печать, размытие при удержании Cmd+Shift и сброс — успешно.");
