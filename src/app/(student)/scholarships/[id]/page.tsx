import { ScholarshipDetail } from "@/features/scholarships/scholarships";
export const metadata = {title: "Scholarship details"};
export default async function Page({params}: {params: Promise<{id:string}>}) {
 const {id}=await params;
 return <ScholarshipDetail id={id}/>;
}
