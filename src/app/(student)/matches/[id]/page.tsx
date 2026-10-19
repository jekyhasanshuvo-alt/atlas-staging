import { ProgramProfileAssessment } from "@/features/matching/matching";
export const metadata = { title: "Private program assessment" };
export default async function Page({ params }: {
    params: Promise<{
        id: string;
    }>;
}) { const { id } = await params; return <ProgramProfileAssessment id={id}/>; }
