import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const listeners = new Map();
const classes = new Set();
let timer;
const context = vm.createContext({
  atob,
  clearTimeout: () => {},
  crypto: webcrypto,
  document: {
    addEventListener: (name, callback) => listeners.set(name, callback),
    documentElement: {classList: {
      add: name => classes.add(name),
      remove: name => classes.delete(name),
      toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
    }},
    getElementById: () => ({textContent: ""}),
  },
  sessionStorage: {getItem: key => key === "timp-copy-unlocked" ? "yes" : null},
  setTimeout: callback => {timer = callback; return 1;},
  TextDecoder,
  TextEncoder,
});
vm.runInContext(readFileSync(new URL("web/protect.js", import.meta.url), "utf8"), context);

assert.equal(vm.runInContext("unlocked", context), false);
assert.equal(await vm.runInContext('validPassword("admin")', context), true);
assert.equal(await vm.runInContext('validPassword("timp-demo-2026")', context), false);

let prevented = false;
const keydown = listeners.get("keydown");
keydown({metaKey: true, shiftKey: true, code: "KeyK", key: "K", preventDefault: () => {prevented = true;}});
assert.equal(classes.has("screenshot-blur"), false);
assert.equal(prevented, false);
keydown({metaKey: true, shiftKey: true, code: "Digit4", key: "4", preventDefault: () => {prevented = true;}});
assert.equal(classes.has("screenshot-blur"), true);
assert.equal(prevented, true);
timer();
assert.equal(classes.has("screenshot-blur"), false);

console.log("Веб-проверка: пароль admin, отказ старому паролю и реакция на ⌘⇧4 — успешно.");
