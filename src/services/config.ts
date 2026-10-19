export const dataMode = process.env.NEXT_PUBLIC_ATLAS_DATA_MODE ?? "demo";
if (dataMode !== "demo" && dataMode !== "api")
  throw new Error("NEXT_PUBLIC_ATLAS_DATA_MODE must be demo or api");
const configuredBase =
  process.env.NEXT_PUBLIC_ATLAS_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const url = new URL(configuredBase);
if (!["http:", "https:"].includes(url.protocol) || url.username || url.password)
  throw new Error("Configure a credential-free HTTP(S) API URL");
export const apiBaseUrl = configuredBase.replace(/\/$/, "");
