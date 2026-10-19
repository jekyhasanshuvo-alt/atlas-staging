import { ApplicationJourney } from "@/features/applications/applications";
export default async function ApplicationPage({ params }: {
    params: Promise<{
        id: string;
    }>;
}) { const { id } = await params; return <ApplicationJourney id={id}/>; }
