import { IntelligenceExplorer } from "@/features/intelligence/intelligence";
export const metadata = { title: "University explorer" };
export default function Page() {
  return <IntelligenceExplorer kind="universities" />;
}
