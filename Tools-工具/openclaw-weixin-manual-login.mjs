const accountId = process.argv[2] || "default";
const loginTimeoutMs = 8 * 60 * 1000;

console.log(`Starting Weixin manual login for account: ${accountId}`);
console.log("Loading OpenClaw Weixin modules...");

const { normalizeAccountId } = await import("file:///C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/dist/plugin-sdk/account-id.js");
const {
  DEFAULT_ILINK_BOT_TYPE,
  displayQRCode,
  startWeixinLoginWithQr,
  waitForWeixinLogin,
} = await import("file:///C:/Users/Administrator/.openclaw/npm/node_modules/@tencent-weixin/openclaw-weixin/dist/src/auth/login-qr.js");
const {
  registerWeixinAccountId,
  saveWeixinAccount,
  DEFAULT_BASE_URL,
} = await import("file:///C:/Users/Administrator/.openclaw/npm/node_modules/@tencent-weixin/openclaw-weixin/dist/src/auth/accounts.js");

console.log("Modules loaded.");

const start = await startWeixinLoginWithQr({
  accountId,
  apiBaseUrl: DEFAULT_BASE_URL,
  botType: DEFAULT_ILINK_BOT_TYPE,
  verbose: true,
});

if (!start.qrcodeUrl) {
  throw new Error(start.message);
}

console.log("\nScan this QR code with WeChat to connect OpenClaw:\n");
await displayQRCode(start.qrcodeUrl);
console.log(`\nQR URL: ${start.qrcodeUrl}\n`);
console.log("Waiting for scan/confirmation...");

const result = await waitForWeixinLogin({
  sessionKey: start.sessionKey,
  apiBaseUrl: DEFAULT_BASE_URL,
  timeoutMs: loginTimeoutMs,
  verbose: true,
  botType: DEFAULT_ILINK_BOT_TYPE,
});

if (result.connected && result.botToken && result.accountId) {
  const normalizedId = normalizeAccountId(result.accountId);
  saveWeixinAccount(normalizedId, {
    token: result.botToken,
    baseUrl: result.baseUrl,
    userId: result.userId,
  });
  registerWeixinAccountId(normalizedId);
  console.log(`\nConnected. Saved Weixin account: ${normalizedId}`);
  process.exit(0);
}

if (result.alreadyConnected) {
  console.log(`\nAlready connected: ${result.message}`);
  process.exit(0);
}

throw new Error(result.message);
