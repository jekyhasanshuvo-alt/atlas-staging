export const dataMode = process.env.NEXT_PUBLIC_ATLAS_DATA_MODE ?? "demo";
if (dataMode !== "demo" && dataMode !== "api")
  throw new Error("NEXT_PUBLIC_ATLAS_DATA_MODE must be demo or api");
const configuredBase =
  process.env.NEXT_PUBLIC_ATLAS_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
if (configuredBase !== "/api/v1") {
  const url = new URL(configuredBase);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password)
    throw new Error("Configure a credential-free HTTP(S) API URL");
}
if (process.env.NEXT_PUBLIC_ATLAS_STAGING_DEMO === "true" &&
    (dataMode !== "api" || configuredBase !== "/api/v1"))
  throw new Error("Staging requires API mode and the same-origin proxy");
export const apiBaseUrl = configuredBase.replace(/\/$/, "");
export const apiV2BaseUrl = apiBaseUrl === "/api/v1" ? "/api/v2" :
  new URL("../v2", apiBaseUrl + "/").href.replace(/\/$/, "");
