// Реальные снимки работающего интерфейса. Требуется установленный Google Chrome.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from 'playwright';

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8084';
const root = resolve(import.meta.dirname, '../..');
const shots = resolve(root, 'screenshots');
const evidence = resolve(root, 'verification');
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });
const runId = Date.now().toString(36);
const users = { owner: `ivan.${runId}`, reader: `grigory.${runId}`, outsider: `observer.${runId}` };
const password = 'Lab4-DemoPass1!';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const errors = [];
const checks = [];
const network = [];

async function pageFor() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1120 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {
    if (response.url().includes('/api/')) {
      const url = new URL(response.url());
      network.push({ method: response.request().method(), path: url.pathname, status: response.status() });
    }
  });
  return page;
}

async function submitCredentials(page, login, pass, action) {
  await page.getByLabel('Логин', { exact: true }).fill(login);
  await page.getByLabel('Пароль', { exact: true }).fill(pass);
  await Promise.all([
    page.waitForResponse(r => /\/api\/(register|login)$/.test(r.url()) && r.request().method() === 'POST'),
    page.getByRole('button', { name: action }).click(),
  ]);
}
async function status(page, expected, message) {
  const notice = page.getByRole('status');
  await notice.getByText(`HTTP ${expected}`, { exact: true }).waitFor();
  if (message) assert.match(await notice.innerText(), message);
  checks.push({ name: message?.source || `HTTP ${expected}`, status: expected, passed: true });
}
async function login(page, user) {
  await page.goto(baseURL + '/login');
  await submitCredentials(page, user, password, 'Войти в систему');
  await page.getByRole('heading', { name: 'Ваши ресурсы. Ваши правила.' }).waitFor();
}
async function shot(page, file) {
  await page.screenshot({ path: resolve(shots, file), fullPage: true });
}

try {
  const owner = await pageFor();
  await owner.goto(baseURL + '/register');
  await shot(owner, '01-register-form.png');
  for (const user of Object.values(users)) {
    await submitCredentials(owner, user, password, 'Создать учётную запись');
    await status(owner, 201, /Пользователь создан/);
  }
  await shot(owner, '02-register-success.png');
  await owner.setViewportSize({ width: 760, height: 1120 });
  const formBox = await owner.locator('.auth-card').boundingBox();
  const noticeBox = await owner.getByRole('status').boundingBox();
  await owner.screenshot({ path: resolve(shots, '12-register-detail.png'), clip: {
    x: formBox.x, y: noticeBox.y, width: formBox.width, height: formBox.y + formBox.height - noticeBox.y,
  } });
  await owner.setViewportSize({ width: 1440, height: 1120 });
  await submitCredentials(owner, users.owner, password, 'Создать учётную запись');
  await status(owner, 409, /логин уже занят/);
  await shot(owner, '03-register-duplicate.png');
  await submitCredentials(owner, `weak.${runId}`, 'weak', 'Создать учётную запись');
  await status(owner, 422, /Проверьте данные/);
  await shot(owner, '04-register-validation.png');
  await login(owner, users.owner);
  await owner.getByText('+ Создать ресурс', { exact: true }).click();
  await owner.getByLabel('Название нового ресурса', { exact: true }).fill('План лабораторной работы');
  await owner.getByLabel('Содержимое нового ресурса', { exact: true }).fill('Вариант 2. Проверить регистрацию, выдачу прав и отказ в доступе.');
  await owner.getByRole('button', { name: 'Создать ресурс', exact: true }).click();
  await status(owner, 201, /Ресурс #\d+ создан/);
  const resourceId = await owner.getByLabel('Номер ресурса', { exact: true }).inputValue();
  await owner.locator('summary').click();
  await owner.getByLabel('Логин участника', { exact: true }).fill(users.reader);
  await owner.getByRole('button', { name: 'Сохранить права', exact: true }).click();
  await status(owner, 200, /Права пользователя .* сохранены/);
  await owner.locator('.grant').filter({ hasText: users.reader }).waitFor();
  await shot(owner, '05-owner-grant.png');
  await owner.setViewportSize({ width: 1000, height: 1120 });
  await owner.locator('.permission-card').screenshot({ path: resolve(shots, '13-grant-detail.png') });
  await owner.setViewportSize({ width: 1440, height: 1120 });

  const reader = await pageFor();
  await login(reader, users.reader);
  await reader.getByRole('button', { name: /План лабораторной работы/ }).click();
  await reader.getByRole('button', { name: 'Прочитать', exact: true }).click();
  await status(reader, 200, /Чтение ресурса .* разрешено/);
  assert.match(await reader.locator('.document-card textarea').inputValue(), /Вариант 2/);
  await shot(reader, '06-reader-allowed.png');
  await reader.setViewportSize({ width: 760, height: 1120 });
  await reader.locator('.document-card').screenshot({ path: resolve(shots, '14-read-detail.png') });
  await reader.setViewportSize({ width: 1440, height: 1120 });
  await reader.locator('.document-card textarea').fill('Попытка изменения с одним правом чтения.');
  await reader.getByRole('button', { name: 'Сохранить', exact: true }).click();
  await status(reader, 403, /Доступ запрещён/);
  await shot(reader, '07-reader-update-denied.png');

  const outsider = await pageFor();
  await login(outsider, users.outsider);
  assert.equal(await outsider.locator('.resource').count(), 0);
  await outsider.getByLabel('Номер ресурса', { exact: true }).fill(resourceId);
  await outsider.getByRole('button', { name: 'Прочитать', exact: true }).click();
  await status(outsider, 403, /Доступ запрещён/);
  assert.equal(await outsider.locator('.document-card textarea').inputValue(), '');
  await shot(outsider, '08-outsider-denied.png');
  await outsider.setViewportSize({ width: 760, height: 1120 });
  await outsider.getByRole('status').screenshot({ path: resolve(shots, '15-denied-notice.png') });
  await outsider.locator('.document-card').screenshot({ path: resolve(shots, '16-denied-detail.png') });

  await owner.getByRole('button', { name: 'Отозвать', exact: true }).click();
  await status(owner, 204, /отозваны/);
  await reader.getByRole('button', { name: 'Прочитать', exact: true }).click();
  await status(reader, 403, /Доступ запрещён/);
  await shot(reader, '09-reader-revoked.png');
  // Оставляем воспроизводимый демонстрационный пример с правом чтения.
  await owner.getByRole('button', { name: 'Сохранить права', exact: true }).click();
  await status(owner, 200, /сохранены/);

  await outsider.setViewportSize({ width: 390, height: 844 });
  assert.equal(await outsider.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await shot(outsider, '10-mobile.png');
  checks.push({ name: 'mobile_has_no_horizontal_overflow', passed: true });
  assert.deepEqual(errors, []);
  await writeFile(resolve(evidence, 'ui.json'), JSON.stringify({
    executed_at: new Date().toISOString(), base_url: baseURL, browser: await browser.version(),
    users, resource_id: Number(resourceId), checks, network, browser_errors: errors,
  }, null, 2) + '\n');
  console.log(`UI: ${checks.length} проверок выполнено; скриншоты: ${shots}`);
} finally { await browser.close(); }
