import { apiBaseUrl, offlineDemo } from "./config";
import { validateStudentResponse } from "./student-contracts";
import type { Student, FinancialPlan } from "@/types";

export class StudentApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function studentRequest<T>(
  path: string,
  method = "GET",
  body?: unknown,
  csrf = "atlas",
): Promise<T> {
  if (offlineDemo) throw new StudentApiError(503, "Accounts and API access are disabled in this offline demo.");
  let response: Response;
  try {
    response = await fetch(apiBaseUrl + path, {
      method,
      credentials: "include",
      cache: "no-store",
      signal: AbortSignal.timeout(12000),
      headers: {
        "Content-Type": "application/json",
        ...(method !== "GET" ? { "X-Atlas-CSRF": csrf } : {}),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new StudentApiError(
      0,
      "The account server is unavailable. Your draft is preserved. Please retry.",
    );
  }
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new StudentApiError(
      response.status,
      data?.error?.message ?? "The request could not be completed.",
    );
  if (response.status === 204 && method === "DELETE") return undefined as T;
  if (data === null)
    throw new StudentApiError(
      0,
      "The account server returned an invalid response.",
    );
  return validateStudentResponse(path, method, data) as T;
}
export interface Account {
  id: string;
  email: string;
  email_verified: boolean;
}
export interface Identity {
  user: Account;
  csrf_token: string;
}
export interface CloudProfile {
  full_name: string;
  nationality: string;
  current_country: string;
  preferred_destination: string;
  education_level: string;
  academic_background: string;
  preferred_subject: string;
  budget_amount: string;
  budget_currency: "CNY" | "USD" | "BDT";
  language_proficiency: string;
  scholarship_preference: boolean;
  career_goals: string;
  onboarding_completed_at: string | null;
}
export const emptyStudent: Student = {
  fullName: "",
  nationality: "",
  currentCountry: "",
  destination: "",
  education: "High school",
  background: "",
  subject: "",
  budget: 0,
  language: "",
  scholarship: false,
  careerGoals: "",
};
export function toStudent(p: CloudProfile): Student {
  return {
    fullName: p.full_name,
    nationality: p.nationality,
    currentCountry: p.current_country,
    destination: p.preferred_destination,
    education: p.education_level,
    background: p.academic_background,
    subject: p.preferred_subject,
    budget: Number(p.budget_amount),
    language: p.language_proficiency,
    scholarship: p.scholarship_preference,
    careerGoals: p.career_goals,
  };
}
export function toProfile(p: Student) {
  return {
    full_name: p.fullName,
    nationality: p.nationality,
    current_country: p.currentCountry,
    preferred_destination: p.destination,
    education_level: p.education,
    academic_background: p.background,
    preferred_subject: p.subject,
    budget_amount: p.budget,
    budget_currency: "CNY",
    language_proficiency: p.language,
    scholarship_preference: p.scholarship,
    career_goals: p.careerGoals,
  };
}
export interface CloudWorkspace {
  profile: CloudProfile;
  universities: string[];
  scholarships: string[];
  comparison: string[];
  checklists: Record<string, string[]>;
}
export interface CloudPlan
  extends Omit<
    FinancialPlan,
    | "tuition"
    | "accommodation"
    | "food"
    | "transportation"
    | "insurance"
    | "other"
    | "scholarship"
    | "relocation"
    | "emergency"
  > {
  id: string;
  name: string;
  version: number;
  tuition: string;
  accommodation: string;
  food: string;
  transportation: string;
  insurance: string;
  other: string;
  scholarship: string;
  relocation: string;
  emergency: string;
  baseline: Record<string, unknown> | null;
}
export function planValues(
  p: CloudPlan | Record<string, unknown>,
): FinancialPlan {
  return {
    country: String(p.country),
    university: String(p.university),
    currency: String(p.currency),
    years: Number(p.years),
    tuition: Number(p.tuition),
    accommodation: Number(p.accommodation),
    food: Number(p.food),
    transportation: Number(p.transportation),
    insurance: Number(p.insurance),
    other: Number(p.other),
    scholarship: Number(p.scholarship),
    relocation: Number(p.relocation),
    emergency: Number(p.emergency),
  };
}
export function safeReturnTo(value: string | null) {
  if (!value || !/^\/(?!\/)/.test(value) || /[\\\x00-\x20]/.test(value))
    return "/dashboard";
  try {
    const url = new URL(value, "https://atlas.invalid");
    return url.origin === "https://atlas.invalid" &&
      !["/login", "/signup", "/reset-password", "/verify-email"].includes(
        url.pathname,
      )
      ? url.pathname + url.search
      : "/dashboard";
  } catch {
    return "/dashboard";
  }
}
