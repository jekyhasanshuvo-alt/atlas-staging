import { offlineDemo } from "@/services/config";
import { PublicShell } from "@/components/layout/public-shell";
export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  if (offlineDemo) return <>{children}</>;
  return <PublicShell>{children}</PublicShell>;
}
