import { IntelligenceDetail } from "@/features/intelligence/intelligence";
export const dynamic = "force-dynamic";
export const metadata = { title: "University intelligence" };
export default async function Page({ params, }: {
    params: Promise<{
        id: string;
    }>;
}) {
    const { id } = await params;
    return <IntelligenceDetail kind="universities" id={id}/>;
}
