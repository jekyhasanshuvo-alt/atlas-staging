import { z } from "zod";
const decimal = z
  .union([z.string().regex(/^\d+(\.\d+)?$/), z.number()])
  .transform(Number)
  .pipe(z.number().finite().nonnegative());
const currency = z.string().regex(/^[A-Z]{3}$/);
const timestamp = z.iso.datetime({ offset: true }).nullable();
const externalUrl = z
  .string()
  .url()
  .refine((value) => {
    try {
      const url = new URL(value);
      return (
        ["http:", "https:"].includes(url.protocol) &&
        !url.username &&
        !url.password
      );
    } catch {
      return false;
    }
  }, "Only credential-free HTTP(S) sources are allowed")
  .nullable();
export const statusSchema = z.enum([
  "unverified",
  "under_review",
  "verified",
  "stale",
  "rejected",
]);
export const provenanceSchema = z.object({
  is_demo: z.boolean(),
  verification_status: statusSchema,
  records: z.array(
    z.object({
      entity_type: z.string(),
      entity_id: z.string(),
      verification_status: statusSchema,
      reviewed_at: timestamp,
      reviewed_fields: z.array(z.string()),
      valid_from: timestamp,
      valid_until: timestamp,
      notes: z.string(),
      source: z.object({
        id: z.string(),
        source_type: z.string(),
        title: z.string(),
        source_url: externalUrl,
        publisher: z.string(),
        retrieved_at: timestamp,
      }),
    }),
  ),
});
export type Provenance = z.infer<typeof provenanceSchema>;
export const countrySchema = z.object({
  id: z.string(),
  name: z.string(),
  iso_code: z.string().length(2),
  currency_code: currency,
});
export const costSchema = z.object({
  amount: decimal,
  currency,
  period: z.string(),
  provenance: provenanceSchema,
});
export const programSchema = z.object({
  id: z.string(),
  name: z.string(),
  degree_level: z.enum(["Bachelor", "Master", "PhD"]),
  field_of_study: z.string(),
  language_of_instruction: z.string(),
  duration_months: z.number().int().positive(),
  tuition_amount: decimal.nullable(),
  tuition_currency: currency,
  tuition_period: z.enum(["year", "semester", "month", "degree"]),
  scholarship_ids: z.array(z.string()),
  provenance: provenanceSchema,
});
export const universitySchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  short_name: z.string(),
  color: z.enum(["blue", "teal", "violet", "amber", "rose"]),
  country: countrySchema,
  city: z.object({ id: z.string(), name: z.string(), country_id: z.string() }),
  official_website: externalUrl,
  description: z.string(),
  institution_type: z.string(),
  status: z.string(),
  programs: z.array(programSchema),
  living_cost: costSchema.nullable(),
  provenance: provenanceSchema,
});
export const scholarshipSchema = z.object({
  id: z.string(),
  name: z.string(),
  provider: z.string(),
  description: z.string(),
  funding_type: z.enum(["Full", "Partial"]),
  funding_amount: decimal.nullable(),
  funding_currency: currency.nullable(),
  eligibility_summary: z.string(),
  application_deadline: z.iso.date().nullable(),
  official_url: externalUrl,
  coverage: z.string(),
  countries: z.array(countrySchema),
  degree_levels: z.array(z.enum(["Bachelor", "Master", "PhD"])),
  program_ids: z.array(z.string()),
  provenance: provenanceSchema,
});
export const financialReferenceSchema = z.object({
  program_id: z.string(),
  university_id: z.string(),
  university_name: z.string(),
  country: countrySchema,
  program_name: z.string(),
  tuition_amount: decimal.nullable(),
  tuition_currency: currency,
  tuition_period: z.enum(["year", "semester", "month", "degree"]),
  duration_months: z.number().int().positive(),
  provenance: provenanceSchema,
  living_cost: costSchema.nullable(),
});
export type FinancialReference = z.infer<typeof financialReferenceSchema>;
export const pageSchema = <T extends z.ZodType>(item: T) =>
  z.object({
    items: z.array(item),
    meta: z.object({
      page: z.number().int().positive(),
      page_size: z.number().int().positive().max(100),
      total: z.number().int().nonnegative(),
      pages: z.number().int().nonnegative(),
    }),
  });
export interface Paginated<T> {
  items: T[];
  meta: { page: number; page_size: number; total: number; pages: number };
}

export const optionsSchema = z.object({
  subjects: z.array(z.string()),
  cities: z.array(
    z.object({ id: z.string(), name: z.string(), country_id: z.string() }),
  ),
});
