import type { University } from "@/types";
export interface UniversityFilters {
  query: string;
  country: string;
  degree: string;
  subject: string;
  maxTuition: number;
  scholarship: boolean;
  sort: string;
}
export const defaultFilters: UniversityFilters = {
  query: "",
  country: "",
  degree: "",
  subject: "",
  maxTuition: 60000,
  scholarship: false,
  sort: "name",
};
export function filterUniversities(data: University[], f: UniversityFilters) {
  return data
    .filter(
      (u) =>
        (u.name + " " + u.city)
          .toLowerCase()
          .includes(f.query.trim().toLowerCase()) &&
        (!f.country || u.country === f.country) &&
        u.programs.some(
          (p) =>
            (!f.degree || p.degree === f.degree) &&
            (!f.subject || p.subject === f.subject),
        ) &&
        u.tuition !== null &&
        u.tuition <= f.maxTuition &&
        (!f.scholarship || u.scholarship),
    )
    .sort((a, b) =>
      f.sort === "tuition"
        ? (a.tuition ?? Infinity) - (b.tuition ?? Infinity)
        : f.sort === "living"
          ? (a.living ?? Infinity) - (b.living ?? Infinity)
          : a.name.localeCompare(b.name),
    );
}
export function toggleComparison(ids: string[], id: string) {
  return ids.includes(id)
    ? ids.filter((x) => x !== id)
    : ids.length < 4
      ? [...ids, id]
      : ids;
}
