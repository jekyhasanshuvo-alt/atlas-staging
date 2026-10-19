import { OfflineDemoBoundary } from "@/components/offline-demo-boundary";
import { offlineDemo } from "@/services/config";
import type { Metadata } from "next";
import { StudentProvider } from "@/components/auth/student-provider";
import "@/styles/auth.css";
import "@/styles/globals.css";
import "@/styles/dashboard.css";
import "@/styles/features.css";
import "@/styles/marketing.css";
import "@/styles/responsive.css";
import "@/styles/catalog.css";
export const metadata: Metadata = {
  title: {
    default: "Atlas — Your world, within reach",
    template: "%s | Atlas",
  },
  description:
    "A thoughtful student intelligence workspace. Discover universities, explore sample scholarships, and plan your study journey.",
  referrer: "no-referrer",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-scroll-behavior="smooth" suppressHydrationWarning>
      <body>
        {process.env.NEXT_PUBLIC_ATLAS_STAGING_DEMO === "true" && (
          <p role="note" className="staging-demo-notice">
            Fictional hackathon demo — no real student data or verified awards.
            The catalog is empty. Enter your own financial assumptions; initial zeros
            are placeholders, not known free costs. Funding and FX are not guaranteed.
          </p>
        )}
        {offlineDemo ? <OfflineDemoBoundary><StudentProvider>{children}</StudentProvider></OfflineDemoBoundary> : <StudentProvider>{children}</StudentProvider>}
      </body>
    </html>
  );
}
