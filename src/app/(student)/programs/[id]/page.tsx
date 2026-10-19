import { IntelligenceDetail } from "@/features/intelligence/intelligence";
export const metadata = { title: "Program intelligence" };
export default async function Page({ params }: {
    params: Promise<{
        id: string;
    }>;
}) {
    const { id } = await params;
    return <IntelligenceDetail kind="programs" id={id}/>;
}
