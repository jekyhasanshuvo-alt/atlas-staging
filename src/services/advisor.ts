import { z } from "zod";
import type { Requester } from "./profile-intelligence";
import { scenarioResultSchema, type ScenarioRequest } from "./financial-scenarios";
const status = z.enum(["unverified", "under_review", "verified", "stale", "rejected"]);
export const intents = ["auto", "university", "program", "compare", "scholarship", "matching", "financial", "planning", "eligibility"] as const;
const citation = z.object({ id: z.string(), review_context: z.string(), entity_id: z.string(), entity_kind: z.enum(["university", "program", "scholarship"]), field: z.string(), source_id: z.string(), source_title: z.string(), source_url: z.string().nullable(), publisher: z.string(), source_type: z.string(), retrieved_at: z.string().nullable(), reviewed_at: z.string().nullable(), verification_status: status, role: z.enum(["supports_stored_field", "context_only"]), freshness: z.enum(["stored_snapshot_current_review", "freshness_unknown", "not_current_support"]), intake: z.null(), capture_timestamp: z.null(), applicability: z.string() });
export const advisorAnswerSchema = z.object({ status: z.enum(["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT_EVIDENCE", "UNSUPPORTED", "SAFETY_REFUSAL", "INTERNAL_ERROR"]), code: z.enum(["ADVISOR_OK", "ADVISOR_PARTIAL", "ADVISOR_EVIDENCE_MISSING", "ADVISOR_UNSUPPORTED", "ADVISOR_REFUSED", "ADVISOR_INTERNAL"]), intent: z.string(), scope: z.enum(["general", "selected_catalog", "request_scoped"]), summary: z.string(),
    claims: z.array(z.object({ id: z.string(), text: z.string(), entity_id: z.string().nullable(), field: z.string().nullable(), value: z.string().nullable(), basis: z.enum(["stored_catalog", "supported_stored_field", "general_guidance", "explicit_user_preference", "hypothetical_scenario", "user_managed_stage"]), verification_status: status, supporting_citation_ids: z.array(z.string()), context_citation_ids: z.array(z.string()) })).max(64), citations: z.array(citation).max(64), unknowns: z.array(z.string()), limitations: z.array(z.string()), follow_ups: z.array(z.string()), unavailable_ids: z.array(z.string()), scenario_result: scenarioResultSchema.nullable(), eligibility_status: z.literal("NOT_ASSESSED"), provider: z.literal("offline_rules_v1"), external_inference: z.literal(false), conversation_stored: z.literal(false), live_sources_fetched: z.literal(false) }).superRefine((value, ctx) => {
    const refs = new Map(value.citations.map(c => [c.id, c]));
    if (refs.size !== value.citations.length)
        ctx.addIssue({ code: "custom", message: "Duplicate advisor citation identity" });
    const codes = { SUPPORTED: "ADVISOR_OK", PARTIALLY_SUPPORTED: "ADVISOR_PARTIAL", INSUFFICIENT_EVIDENCE: "ADVISOR_EVIDENCE_MISSING", UNSUPPORTED: "ADVISOR_UNSUPPORTED", SAFETY_REFUSAL: "ADVISOR_REFUSED", INTERNAL_ERROR: "ADVISOR_INTERNAL" };
    if (codes[value.status] !== value.code)
        ctx.addIssue({ code: "custom", message: "Inconsistent advisor status" });
    for (const claim of value.claims)
        for (const id of [...claim.supporting_citation_ids, ...claim.context_citation_ids]) {
            const ref = refs.get(id);
            if (!ref || ref.entity_id !== claim.entity_id || ref.field !== claim.field || (claim.supporting_citation_ids.includes(id) && (ref.role !== "supports_stored_field" || ref.verification_status !== "verified")))
                ctx.addIssue({ code: "custom", message: "Unbound advisor citation" });
        }
});
export const advisorCapabilitySchema = z.object({ available: z.literal(true), provider: z.literal("offline_rules_v1"), external_inference: z.literal(false), conversation_stored: z.literal(false), private_context: z.literal("explicit_request_only"), operational_journey: z.literal(false), eligibility_status: z.literal("NOT_ASSESSED") });
export type AdvisorAnswer = z.infer<typeof advisorAnswerSchema>;
export type AdvisorRequest = {
    question: string;
    intent: typeof intents[number];
    entity_ids: string[];
    search: string;
    preferences?: {
        degree?: "Bachelor" | "Master" | "PhD";
        subject?: string;
        language?: string;
    };
    scenario?: ScenarioRequest;
    personal_stage?: string;
};
export async function advisorCapability(send: Requester) {
    const data = advisorCapabilitySchema.safeParse(await send<unknown>("/advisor/capabilities"));
    if (!data.success)
        throw new Error("Advisor capability is incompatible. No request was sent to a model.");
    return data.data;
}
export async function askAdvisor(send: Requester, request: AdvisorRequest) {
    const data = advisorAnswerSchema.safeParse(await send<unknown>("/advisor/ask", "POST", request));
    if (!data.success)
        throw new Error("Advisor returned an incompatible or unbound response. No conversation was saved.");
    return data.data;
}
