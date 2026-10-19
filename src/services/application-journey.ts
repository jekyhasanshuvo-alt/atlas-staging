import { z } from "zod";
import type { Requester } from "./profile-intelligence";
export const stages = ["RESEARCHING", "SHORTLISTED", "PREPARING", "READY_TO_SUBMIT", "SUBMITTED", "UNDER_REVIEW", "OFFER_RECEIVED", "REJECTED", "WITHDRAWN", "ENROLLED"] as const;
export const documentStates = ["NOT_STARTED", "IN_PROGRESS", "READY", "SUBMITTED", "NOT_APPLICABLE"] as const;
const nullableText = z.string().nullable();
const version = z.number().int().positive();
const stamp = z.string().datetime({ offset: true });
export const applicationSchema = z.object({ id: z.uuid(), label: z.string(), university_id: z.string(), program_id: nullableText,
    cycle_key: nullableText, route_key: nullableText, stage: z.enum(stages), archived: z.boolean(), version,
    created_at: stamp, updated_at: stamp, link_available: z.boolean(), stage_basis: z.literal("user_managed_not_verified"),
    official_requirements: z.literal("UNKNOWN"), official_deadline: z.literal("UNKNOWN") });
export const itemSchema = z.object({ id: z.uuid(), application_id: z.uuid(), kind: z.enum(["task", "document", "reminder", "note"]),
    title: z.string(), description: nullableText, completed: z.boolean().nullable(), priority: z.enum(["low", "normal", "high"]).nullable(),
    document_state: z.enum(documentStates).nullable(), due_date: nullableText, reminder_mode: z.enum(["date", "instant"]).nullable(),
    reminder_date: nullableText, reminder_at: stamp.nullable(), timezone: nullableText, version, created_at: stamp, updated_at: stamp,
    origin: z.literal("personal_user_created") });
export const eventSchema = z.object({ id: z.uuid(), application_id: z.uuid(), previous_stage: z.enum(stages).nullable(), new_stage: z.enum(stages),
    version, changed_at: stamp, reason: nullableText, basis: z.literal("user_managed_not_verified") });
export const metaSchema = z.object({ page: version, page_size: version, total: z.number().int().nonnegative(), pages: z.number().int().nonnegative() });
export const applicationPageSchema = z.object({ items: z.array(applicationSchema), meta: metaSchema });
export const itemPageSchema = z.object({ items: z.array(itemSchema), meta: metaSchema });
export const eventPageSchema = z.object({ items: z.array(eventSchema), meta: metaSchema });
export const capabilitySchema = z.object({ available: z.literal(true), basis: z.literal("synthetic_disposable_only"), official_requirements: z.literal("UNKNOWN") });
export const dashboardSchema = z.object({ total_applications: z.number().int().nonnegative(), archived_applications: z.number().int().nonnegative(),
    by_stage: z.record(z.string(), z.number().int().nonnegative()), pending_personal_tasks: z.number().int().nonnegative(),
    completed_personal_tasks: z.number().int().nonnegative(), overdue_personal_tasks: z.number().int().nonnegative(),
    upcoming_personal_reminders: z.array(itemSchema), recent_personal_events: z.array(eventSchema), missing_cycle: z.number().int().nonnegative(),
    missing_program: z.number().int().nonnegative(), official_requirements: z.literal("UNKNOWN"), explanation: z.string() });
export type Application = z.infer<typeof applicationSchema>;
export type Item = z.infer<typeof itemSchema>;
export type Dashboard = z.infer<typeof dashboardSchema>;
export function personalLabel(value: string) { return value.toLowerCase().replaceAll("_", " "); }
export function personalDate(item: Pick<Item, "reminder_mode" | "reminder_at" | "reminder_date" | "due_date" | "timezone">) {
    if (item.reminder_mode === "instant" && item.reminder_at && item.timezone) {
        try {
            return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: item.timezone }).format(new Date(item.reminder_at)) + " · " + item.timezone;
        }
        catch {
            return item.reminder_at + " · " + item.timezone;
        }
    }
    return (item.reminder_date ?? item.due_date ?? "Date not set") + (item.timezone ? " · " + item.timezone + " (calendar date)" : "");
}
export async function journeyRequest<T>(send: Requester, path: string, schema: z.ZodType<T>, method = "GET", body?: unknown): Promise<T> {
    const raw = await send<unknown>(path, method, body), result = schema.safeParse(raw);
    if (!result.success)
        throw new Error("Application tracking returned an incompatible response. Retry without changing private data.");
    return result.data;
}
