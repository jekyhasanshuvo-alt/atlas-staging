import { universities, scholarships, student, studyPlan } from "@/data/mock";
import type { University, Scholarship, Degree } from "@/types";
import {
  defaultFilters,
  filterUniversities,
  type UniversityFilters,
} from "@/lib/utils/universities";
import { apiRequest, ApiError, queryParams } from "./api-client";
import { dataMode } from "./config";
import {
  optionsSchema,
  countrySchema,
  universitySchema,
  scholarshipSchema,
  financialReferenceSchema,
  pageSchema,
  type Paginated,
  type FinancialReference,
} from "./contracts";
import { mapUniversity, mapScholarship } from "./mappers";
export const demoRepository = {
  getUniversities: () => universities,
  getUniversity: (id: string) => universities.find((u) => u.id === id),
  getScholarships: () => scholarships,
  getStudent: () => student,
  getStudyPlan: () => studyPlan,
};
export interface UniversityQuery extends UniversityFilters {
  page?: number;
  pageSize?: number;
  ids?: string[];
  city?: string;
  unfiltered?: boolean;
}
export interface ScholarshipQuery {
  query: string;
  country: string;
  degree: string;
  funding: string;
  page?: number;
  pageSize?: number;
  ids?: string[];
}
function paginate<T>(items: T[], page = 1, pageSize = 6): Paginated<T> {
  return {
    items: items.slice((page - 1) * pageSize, page * pageSize),
    meta: {
      page,
      page_size: pageSize,
      total: items.length,
      pages: Math.ceil(items.length / pageSize),
    },
  };
}
export interface CatalogRepository {
  options: () => Promise<{
    subjects: string[];
    cities: { id: string; name: string; country_id: string }[];
  }>;
  universities: (query: UniversityQuery) => Promise<Paginated<University>>;
  university: (identifier: string) => Promise<University | null>;
  scholarships: (query: ScholarshipQuery) => Promise<Paginated<Scholarship>>;
  countries: () => Promise<
    { id: string; name: string; iso_code: string; currency_code: string }[]
  >;
  references: (
    universityId: string,
    page?: number,
  ) => Promise<Paginated<FinancialReference>>;
}
export const mockCatalogRepository: CatalogRepository = {
  async options() {
    return {
      subjects: [
        ...new Set(
          universities.flatMap((u) => u.programs.map((p) => p.subject)),
        ),
      ],
      cities: [...new Set(universities.map((u) => u.city))].map((city) => ({
        id: city.toLowerCase(),
        name: city,
        country_id: "CN",
      })),
    };
  },
  async universities(q) {
    const records = q.ids
      ? universities.filter((u) => q.ids!.includes(u.id))
      : universities;
    return paginate(
      (q.unfiltered
        ? records.filter(
            (u) =>
              (u.name + " " + u.city)
                .toLowerCase()
                .includes(q.query.trim().toLowerCase()) &&
              (!q.country || u.country === q.country),
          )
        : filterUniversities(records, q)
      ).filter((u) => !q.city || u.city === q.city),
      q.page,
      q.pageSize,
    );
  },
  async university(id) {
    return (
      universities.find((u) => u.id === id || u.id + "-university" === id) ??
      null
    );
  },
  async scholarships(q) {
    return paginate(
      scholarships.filter(
        (s) =>
          (s.name + " " + s.description)
            .toLowerCase()
            .includes(q.query.trim().toLowerCase()) &&
          (!q.country || s.country === q.country) &&
          (!q.degree || s.degrees.includes(q.degree as Degree)) &&
          (!q.funding || s.funding === q.funding) &&
          (!q.ids || q.ids.includes(s.id)),
      ),
      q.page,
      q.pageSize,
    );
  },
  async countries() {
    return [{ id: "CN", name: "China", iso_code: "CN", currency_code: "CNY" }];
  },
  async references(id, page = 1) {
    const u = universities.find((u) => u.id === id);
    return paginate(
      u
        ? u.programs.map((p) => ({
            program_id: p.id,
            university_id: u.id,
            university_name: u.name,
            country: {
              id: "CN",
              name: u.country,
              iso_code: "CN",
              currency_code: "CNY",
            },
            program_name: p.degree + " in " + p.subject,
            tuition_amount: u.tuition,
            tuition_currency: "CNY",
            tuition_period: "year" as const,
            duration_months: p.duration * 12,
            provenance: {
              is_demo: true,
              verification_status: "unverified" as const,
              records: [],
            },
            living_cost: null,
          }))
        : [],
      page,
      6,
    );
  },
};
export const apiCatalogRepository: CatalogRepository = {
  async options() {
    return apiRequest("/catalog-options", optionsSchema);
  },
  async universities(q) {
    if (q.ids?.length === 0) return paginate([], q.page, q.pageSize);
    const data = await apiRequest(
      "/universities",
      pageSchema(universitySchema),
      queryParams({
        q: q.query,
        country: q.country,
        city: q.city,
        degree: q.degree,
        subject: q.subject,
        max_tuition: q.unfiltered ? undefined : q.maxTuition,
        tuition_currency: q.unfiltered ? undefined : "CNY",
        scholarship: q.scholarship ? true : undefined,
        sort: q.sort,
        page: q.page ?? 1,
        page_size: q.pageSize ?? 6,
        ids: q.ids,
      }),
    );
    return { ...data, items: data.items.map(mapUniversity) };
  },
  async university(id) {
    try {
      return mapUniversity(
        await apiRequest(
          "/universities/" + encodeURIComponent(id),
          universitySchema,
        ),
      );
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },
  async scholarships(q) {
    if (q.ids?.length === 0) return paginate([], q.page, q.pageSize);
    const data = await apiRequest(
      "/scholarships",
      pageSchema(scholarshipSchema),
      queryParams({
        q: q.query,
        country: q.country,
        degree: q.degree,
        funding: q.funding,
        page: q.page ?? 1,
        page_size: q.pageSize ?? 6,
        ids: q.ids,
      }),
    );
    return { ...data, items: data.items.map(mapScholarship) };
  },
  async countries() {
    return apiRequest("/countries", countrySchema.array());
  },
  async references(id, page = 1) {
    return apiRequest(
      "/financial-reference",
      pageSchema(financialReferenceSchema),
      queryParams({ university_id: id, page, page_size: 6 }),
    );
  },
};
export const catalogRepository =
  dataMode === "api" ? apiCatalogRepository : mockCatalogRepository;
export { defaultFilters };
