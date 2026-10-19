import type { University, Scholarship } from "@/types";
import { z } from "zod";
import { universitySchema, scholarshipSchema } from "./contracts";
import { annualizeTuition } from "@/lib/calculations/reference";
export function mapUniversity(
  dto: z.infer<typeof universitySchema>,
): University {
  const currencies = [
    ...new Set(
      dto.programs
        .filter((p) => p.tuition_amount !== null)
        .map((p) => p.tuition_currency),
    ),
  ];
  const annual =
    currencies.length === 1
      ? dto.programs
          .filter((p) => p.tuition_amount !== null)
          .map((p) =>
            annualizeTuition(
              p.tuition_amount!,
              p.tuition_period,
              p.duration_months,
            ),
          )
      : [];
  return {
    id: dto.id,
    name: dto.name,
    shortName: dto.short_name,
    color: dto.color,
    country: dto.country.name,
    city: dto.city.name,
    description: dto.description,
    tuition: annual.length ? Math.min(...annual) : null,
    tuitionCurrency: currencies.length === 1 ? currencies[0] : undefined,
    living: dto.living_cost?.amount ?? null,
    livingCurrency: dto.living_cost?.currency,
    scholarship: dto.programs.some((p) => p.scholarship_ids.length > 0),
    programs: dto.programs.map((p) => ({
      id: p.id,
      subject: p.field_of_study,
      degree: p.degree_level,
      language: p.language_of_instruction,
      duration: p.duration_months / 12,
      tuitionAmount: p.tuition_amount,
      tuitionCurrency: p.tuition_currency,
      tuitionPeriod: p.tuition_period,
      provenance: p.provenance,
    })),
    provenance: dto.provenance,
    livingProvenance: dto.living_cost?.provenance,
    officialWebsite: dto.official_website,
  };
}
export function mapScholarship(
  dto: z.infer<typeof scholarshipSchema>,
): Scholarship {
  return {
    id: dto.id,
    name: dto.name,
    country:
      dto.countries.map((c) => c.name).join(", ") ||
      "No destination association",
    degrees: dto.degree_levels,
    funding: dto.funding_type,
    description: dto.description,
    coverage: dto.coverage,
    provenance: dto.provenance,
    officialUrl: dto.official_url,
  };
}
