"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PageHeader, ErrorState } from "@/components/shared";
import { DataConnection } from "@/components/shared/catalog";
export function UniversityDetailsUnavailable({ message }: { message: string }) {
  const router = useRouter();
  return (
    <>
      <PageHeader
        title="University catalog unavailable"
        description="This record could not be retrieved. Your saved selections are preserved."
      />
      <DataConnection error={message} />
      <ErrorState message={message} retry={() => router.refresh()} />
      <Link href="/universities" className="text-link">
        Return to explorer
      </Link>
    </>
  );
}
