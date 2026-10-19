import type { University, Scholarship, Student, StudyPlan, FinancialPlan, PreparationTask } from "@/types";
// An empty catalog is intentional: no approved fixtures exist in Neon.
export const universities: University[] = [];
export const scholarships: Scholarship[] = [];
export const student: Student = {
  fullName: "Synthetic Student", nationality: "", currentCountry: "", destination: "",
  education: "", background: "", subject: "", budget: 0, language: "",
  scholarship: false, careerGoals: "Fictional hackathon demonstration only",
};
export const studyPlan: StudyPlan = {
  destination: "", goal: "Create a fictional study plan", intake: "Unknown",
  tasks: [{ id: "demo-estimates", title: "Enter your own assumptions", description: "No institutions, awards or eligibility have been verified in this demo." }],
};
export const defaultPlan: FinancialPlan = {
  country: "", university: "", years: 1, currency: "CNY", tuition: 0, accommodation: 0,
  food: 0, transportation: 0, insurance: 0, other: 0, scholarship: 0,
  relocation: 0, emergency: 0,
};
export const lifeTasks: PreparationTask[] = [];
export const careerTasks: PreparationTask[] = [];
