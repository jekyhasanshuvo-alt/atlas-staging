import { configuredProxy } from "@/server/staging-proxy";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const GET = configuredProxy;
export const POST = configuredProxy;
export const PUT = configuredProxy;
export const PATCH = configuredProxy;
export const DELETE = configuredProxy;
