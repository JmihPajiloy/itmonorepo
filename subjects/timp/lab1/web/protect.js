/* Client-side copy deterrent shared by every page in the two-link chain. */
const verifier = {
  salt: "3oFw/WxuD5GZ9JT3bvplOA==",
  iv: "Fq2GKk7EWzOykR8h",
  ciphertext: "d92DPifxGBxYUaZn+5G7mDAKYf2JRni51IB8"
};
const storageKey = "timp-copy-unlocked-v2";
const decode = value => Uint8Array.from(atob(value), c => c.charCodeAt(0));
let unlocked = sessionStorage.getItem(storageKey) === "yes";
let screenshotBlurTimer;

async function validPassword(password) {
  try {
    const material = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
    const key = await crypto.subtle.deriveKey(
      {name: "PBKDF2", salt: decode(verifier.salt), iterations: 200000, hash: "SHA-256"},
      material, {name: "AES-GCM", length: 256}, false, ["decrypt"]
    );
    const data = await crypto.subtle.decrypt({name: "AES-GCM", iv: decode(verifier.iv)}, key, decode(verifier.ciphertext));
    return new TextDecoder().decode(data) === "unlock-copy";
  } catch (_) {
    return false;
  }
}

function setProtection() {
  document.documentElement.classList.toggle("protected", !unlocked);
  if (unlocked) {
    clearTimeout(screenshotBlurTimer);
    document.documentElement.classList.remove("screenshot-blur");
  }
  document.getElementById("mode").textContent = unlocked ? "Копирование разрешено" : "Копирование ограничено";
  document.getElementById("toggle").textContent = unlocked ? "Включить защиту" : "Отключить по паролю";
}

document.addEventListener("DOMContentLoaded", () => {
  setProtection();
  document.getElementById("toggle").addEventListener("click", async () => {
    if (unlocked) {
      unlocked = false;
      sessionStorage.removeItem(storageKey);
    } else {
      const password = prompt("Пароль отключения защиты:");
      if (password === null) return;
      if (!(await validPassword(password))) {
        alert("Неверный пароль");
        return;
      }
      unlocked = true;
      sessionStorage.setItem(storageKey, "yes");
    }
    setProtection();
  });
});

for (const type of ["copy", "cut", "contextmenu", "dragstart", "selectstart"]) {
  document.addEventListener(type, event => {
    if (!unlocked) event.preventDefault();
  }, true);
}
document.addEventListener("keydown", event => {
  const screenshotKey = /^Digit[3456]$/.test(event.code) || /^[3456]$/.test(event.key);
  if (!unlocked && event.metaKey && event.shiftKey && screenshotKey) {
    event.preventDefault();
    document.documentElement.classList.add("screenshot-blur");
    clearTimeout(screenshotBlurTimer);
    screenshotBlurTimer = setTimeout(() => document.documentElement.classList.remove("screenshot-blur"), 8000);
    return;
  }
  if (!unlocked && (event.ctrlKey || event.metaKey) && ["c", "x", "s", "a", "u"].includes(event.key.toLowerCase())) {
    event.preventDefault();
  }
}, true);
