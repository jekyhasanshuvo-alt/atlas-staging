"use client";
import Link from "next/link";
import { useStudent } from "@/components/auth/student-provider";
export function ProfileAssessmentLink({ id }: {
    id: string;
}) {
    const s = useStudent(), path = "/matches/" + encodeURIComponent(id);
    if (s.loading)
        return <p>Profile comparison requires your account.</p>;
    if (!s.user)
        return <Link className="button" href={"/login?returnTo=" + encodeURIComponent(path)}>Sign in to compare with your profile</Link>;
    if (!s.user.email_verified)
        return <Link className="button" href="/verify-email">Verify email for profile comparisons</Link>;
    return <Link className="button" href={path}>Compare with my profile · Admissions not assessed</Link>;
}
