"use client";
import { ErrorState } from "@/components/shared";
export default function Error({ reset }: { reset: () => void }) {
  return (
    <main className="standalone-state">
      <ErrorState
        message="We couldn’t display this page. Try loading it again."
        retry={reset}
      />
    </main>
  );
}
