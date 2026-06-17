import { readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const openclawHome = join(homedir(), ".openclaw");
const devicePath = join(openclawHome, "identity", "device.json");
const authPath = join(openclawHome, "identity", "device-auth.json");
const pairedPath = join(openclawHome, "devices", "paired.json");

const {
  p: requestDevicePairing,
  n: approveDevicePairing,
  t: approveBootstrapDevicePairing,
} = await import(
  "file:///C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/dist/device-pairing-B1MRm3c4.js"
);
const { t: bootstrapProfile } = await import(
  "file:///C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/dist/device-bootstrap-profile-BNohUA6P.js"
);

const device = JSON.parse(readFileSync(devicePath, "utf8"));
const paired = JSON.parse(readFileSync(pairedPath, "utf8"));
const existing = paired[device.deviceId] ?? {};
const publicKey = existing.publicKey ?? device.publicKeyPem;
const operatorScopes = [...new Set([...(bootstrapProfile.scopes ?? []), "operator.pairing"])];
let requestId = process.argv[2];

if (!device.deviceId) {
  throw new Error("Missing local OpenClaw deviceId.");
}
if (!publicKey) {
  throw new Error("Missing local OpenClaw public key.");
}

if (!requestId) {
  const pending = await requestDevicePairing(
    {
      deviceId: device.deviceId,
      publicKey,
      displayName: existing.displayName ?? "local-cli",
      platform: existing.platform ?? "win32",
      deviceFamily: existing.deviceFamily,
      clientId: existing.clientId ?? "openclaw-cli",
      clientMode: existing.clientMode ?? "cli",
      role: "operator",
      roles: ["operator"],
      scopes: operatorScopes,
      silent: true,
    },
    openclawHome,
  );

  requestId = pending?.requestId ?? pending?.request?.requestId;
}

if (!requestId) {
  throw new Error("OpenClaw did not create a pending device pairing request.");
}

let approved = await approveBootstrapDevicePairing(
  requestId,
  bootstrapProfile,
  openclawHome,
);

if (approved?.status === "forbidden" && approved?.reason === "bootstrap-scope-not-allowed") {
  approved = await approveDevicePairing(
    requestId,
    { callerScopes: operatorScopes },
    openclawHome,
  );
}

if (approved?.status !== "approved") {
  throw new Error(`Bootstrap approval failed: ${JSON.stringify(approved)}`);
}

const operatorToken = approved.device.tokens?.operator;
if (!operatorToken?.token) {
  throw new Error("Bootstrap approval did not return an operator token.");
}

const nextAuth = {
  version: 1,
  deviceId: device.deviceId,
  tokens: {
    operator: {
      token: operatorToken.token,
      role: "operator",
      scopes: operatorToken.scopes ?? [],
      updatedAtMs: Date.now(),
    },
  },
};

writeFileSync(authPath, `${JSON.stringify(nextAuth, null, 2)}\n`, "utf8");

console.log("OpenClaw local operator token refreshed.");
console.log(`Device: ${device.deviceId}`);
console.log(`Operator scopes: ${nextAuth.tokens.operator.scopes.join(", ")}`);
