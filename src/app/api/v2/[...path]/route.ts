// Existing public scholarship/intelligence clients use v2. GET-only allowlist.
import { configuredProxy } from "@/server/staging-proxy";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const GET = configuredProxy;
