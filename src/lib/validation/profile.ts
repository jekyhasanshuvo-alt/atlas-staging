import { z } from "zod";
const text = z
  .string()
  .trim()
  .min(2, "Please enter at least 2 characters.")
  .max(200, "Please use fewer than 200 characters.");
export const profileSchema = z.object({
  fullName: text,
  nationality: text,
  currentCountry: text,
  destination: text,
  education: text,
  background: text,
  subject: text,
  budget: z
    .number()
    .finite()
    .min(1, "Enter a budget greater than zero.")
    .max(100000000),
  language: text,
  scholarship: z.boolean(),
  careerGoals: z
    .string()
    .trim()
    .min(10, "Please describe your goals in at least 10 characters.")
    .max(1000),
});
