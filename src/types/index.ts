import type { Provenance } from "@/services/contracts";
export type Degree = "Bachelor" | "Master" | "PhD";
export interface Program {
  id: string;
  subject: string;
  degree: Degree;
  language: string;
  duration: number;
  tuitionAmount?: number | null;
  tuitionCurrency?: string;
  tuitionPeriod?: "year" | "semester" | "month" | "degree";
  provenance?: Provenance;
}
export interface University {
  id: string;
  name: string;
  shortName: string;
  country: string;
  city: string;
  tuition: number | null;
  tuitionCurrency?: string;
  living: number | null;
  livingCurrency?: string;
  provenance?: Provenance;
  livingProvenance?: Provenance;
  officialWebsite?: string | null;
  scholarship: boolean;
  programs: Program[];
  color: string;
  description: string;
}
export interface Scholarship {
  id: string;
  name: string;
  country: string;
  degrees: Degree[];
  funding: "Full" | "Partial";
  description: string;
  coverage: string;
  provenance?: Provenance;
  officialUrl?: string | null;
}
export interface Student {
  fullName: string;
  nationality: string;
  currentCountry: string;
  destination: string;
  education: string;
  background: string;
  subject: string;
  budget: number;
  language: string;
  scholarship: boolean;
  careerGoals: string;
}
export interface FinancialPlan {
  country: string;
  university: string;
  years: number;
  tuition: number;
  accommodation: number;
  food: number;
  transportation: number;
  insurance: number;
  other: number;
  scholarship: number;
  relocation: number;
  emergency: number;
  currency: string;
}
export interface PreparationTask {
  id: string;
  title: string;
  description: string;
}
export interface StudyPlan {
  destination: string;
  goal: string;
  intake: string;
  tasks: PreparationTask[];
}
