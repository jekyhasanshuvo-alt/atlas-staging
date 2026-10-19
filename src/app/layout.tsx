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
        <StudentProvider>{children}</StudentProvider>
      </body>
    </html>
  );
}
