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

(async () => {
  if (!password) {
    throw new Error("Missing CA01_SYNTHETIC_PASSWORD");
  }
  fs.mkdirSync(artifactDir, { recursive: true });
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
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.locator("#login_email").fill("ca-demo-v1-own-engineer@example.invalid");
  await page.locator("#login_password").fill(password);
  await page
    .locator("button:has-text('Вход в систему'), button:has-text('Login'), button[type='submit']")
    .first()
    .click();
  await page.waitForTimeout(5000);
  const afterLogin = { url: page.url(), body: (await page.locator("body").innerText()).slice(0, 1500) };
  await page.screenshot({ path: path.join(artifactDir, "diagnostic-after-login.png"), fullPage: true });
  await page.goto(`${baseUrl}/app/ferum-service-project/view/list`, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  await page.waitForTimeout(5000);
  const afterList = { url: page.url(), body: (await page.locator("body").innerText()).slice(0, 2000) };
  await page.screenshot({ path: path.join(artifactDir, "diagnostic-list.png"), fullPage: true });
  const summary = { afterLogin, afterList, socketResponses };
  fs.writeFileSync(path.join(artifactDir, "diagnostic-list.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary));
  await browser.close();
})().catch((error) => {
  console.error(String((error && error.stack) || error));
  process.exit(1);
});
