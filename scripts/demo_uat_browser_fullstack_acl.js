const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const runtimeNodeModules = path.join(
  __dirname,
  "..",
  "output",
  "playwright",
  "fullstack_runtime",
  "node_modules",
);
const runtimeRequire = createRequire(path.join(runtimeNodeModules, "index.js"));
const { chromium } = runtimeRequire("playwright-core");

const password = process.env.CA01_SYNTHETIC_PASSWORD;
const baseUrl = "http://ca01.localhost:8000";
const artifactDir = path.join(
  __dirname,
  "..",
  "output",
  "playwright",
  "fullstack_runtime",
  "artifacts",
);
const ownUser = "ca-demo-v1-own-engineer@example.invalid";
const foreignUser = "ca-demo-v1-foreign-engineer@example.invalid";
const ownProject = "CA-DEMO-V1-OWN-PROJECT";
const foreignProject = "CA-DEMO-V1-FOREIGN-PROJECT";

function textLooksForbidden(text) {
  return /403|forbidden|not permitted|no permission|insufficient permission/i.test(text || "");
}

async function loginAndCheck(user, ownName, foreignName, prefix) {
  const browser = await chromium.launch({
    headless: true,
    channel: "msedge",
    args: ["--host-resolver-rules=MAP ca01.localhost 127.0.0.1"],
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const socketResponses = [];
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/socket.io/")) {
      socketResponses.push({ url, status: response.status() });
    }
  });

  const response = await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.locator("#login_email").fill(user);
  await page.locator("#login_password").fill(password);
  await page
    .locator("button:has-text('Вход в систему'), button:has-text('Login'), button[type='submit']")
    .first()
    .click();
  await page.waitForTimeout(5000);
  if (!page.url().includes("/app")) {
    const bodyText = await page.locator("body").innerText();
    throw new Error(`Login did not reach /app for ${user}; url=${page.url()}; body=${bodyText.slice(0, 400)}`);
  }
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});

  await page.goto(`${baseUrl}/app/ferum-service-project/view/list`, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  await page.waitForTimeout(5000);
  const listText = await page.locator("body").innerText();
  const ownVisible = listText.includes(ownName);
  const foreignVisible = listText.includes(foreignName);
  await page.screenshot({ path: path.join(artifactDir, `${prefix}-list.png`), fullPage: true });

  await page.goto(`${baseUrl}/app/ferum-service-project/${ownName}`, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  await page.waitForTimeout(4000);
  const ownFormText = await page.locator("body").innerText();
  const ownFormOk = ownFormText.includes(ownName);
  await page.screenshot({ path: path.join(artifactDir, `${prefix}-own-form.png`), fullPage: true });

  await page.goto(`${baseUrl}/app/ferum-service-project/${foreignName}`, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  await page.waitForTimeout(4000);
  const foreignFormText = await page.locator("body").innerText();
  const foreignDenied = textLooksForbidden(foreignFormText) || !foreignFormText.includes(foreignName);
  await page.screenshot({ path: path.join(artifactDir, `${prefix}-foreign-form.png`), fullPage: true });

  const result = {
    user,
    loginStatus: response && response.status(),
    socketResponses,
    ownVisible,
    foreignVisible,
    ownFormOk,
    foreignDenied,
    currentUrl: page.url(),
  };
  await browser.close();
  return result;
}

(async () => {
  if (!password) {
    throw new Error("Missing CA01_SYNTHETIC_PASSWORD");
  }
  fs.mkdirSync(artifactDir, { recursive: true });
  const own = await loginAndCheck(ownUser, ownProject, foreignProject, "own");
  const foreign = await loginAndCheck(foreignUser, foreignProject, ownProject, "foreign");
  const summary = {
    own,
    foreign,
    allSocketStatuses: [...own.socketResponses, ...foreign.socketResponses].map((row) => row.status),
  };
  fs.writeFileSync(path.join(artifactDir, "fullstack-summary.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary));
})().catch((error) => {
  console.error(String((error && error.stack) || error));
  process.exit(1);
});
