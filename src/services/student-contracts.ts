import { z } from "zod";

const decimal = z.string().regex(/^\d{1,9}(?:\.\d{1,2})?$/);
const text = z.string().max(200);
const id = z.string().min(1).max(120);
const currency = z.enum(["CNY", "USD", "BDT"]);
export const identityContract = z.object({
  user: z.object({
    id: z.uuid(),
    email: z.email(),
    email_verified: z.boolean(),
  }),
  csrf_token: z.string().regex(/^[a-f0-9]{64}$/),
});
export const profileContract = z.object({
  full_name: text,
  nationality: text,
  current_country: text,
  preferred_destination: text,
  education_level: text,
  academic_background: text,
  preferred_subject: text,
  budget_amount: decimal,
  budget_currency: currency,
  language_proficiency: text,
  scholarship_preference: z.boolean(),
  career_goals: z.string().max(1000),
  onboarding_completed_at: z.iso.datetime({ offset: true }).nullable(),
});
const ids = z.array(id).max(500);
const checklists = z.record(z.string(), z.array(z.string()).max(20));
export const workspaceContract = z.object({
  profile: profileContract,
  universities: ids,
  scholarships: ids,
  comparison: ids.max(4),
  checklists,
});
const planValues = z.object({
  country: text,
  university: id.or(z.literal("")),
  currency,
  years: z.number().int().min(1).max(10),
  tuition: decimal,
  accommodation: decimal,
  food: decimal,
  transportation: decimal,
  insurance: decimal,
  other: decimal,
  scholarship: decimal,
  relocation: decimal,
  emergency: decimal,
});
export const planContract = planValues.extend({
  id: z.uuid(),
  name: z.string().min(1).max(120),
  version: z.number().int().positive(),
  baseline: planValues.nullable(),
});
const page = z.object({ items: z.array(planContract).max(100) });
export function validateStudentResponse(
  path: string,
  method: string,
  data: unknown,
): unknown {
  const pathname = path.split("?")[0];
  const contract =
    pathname === "/auth/me" || pathname === "/auth/login"
      ? identityContract
      : pathname === "/me/workspace"
        ? workspaceContract
        : pathname === "/me/profile"
          ? profileContract
          : pathname === "/me/financial-plans" && method === "GET"
            ? page
            : pathname.startsWith("/me/financial-plans") && method !== "DELETE"
              ? planContract
              : null;
  if (!contract) return data;
  const parsed = contract.safeParse(data);
  if (!parsed.success)
    throw new Error(
      "The account server returned an incompatible response. Please retry.",
    );
  return parsed.data;
}
