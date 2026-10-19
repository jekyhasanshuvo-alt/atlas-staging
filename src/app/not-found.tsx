import { EmptyState } from "@/components/shared";
export default function NotFound() {
  return (
    <main className="standalone-state">
      <EmptyState
        title="This page is off the map"
        description="The page or sample university you requested could not be found."
        href="/universities"
      />
    </main>
  );
}
