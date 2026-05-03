"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Globe, Scan, Bug, Gauge, Inbox, FileText, BookOpen, Activity } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", Icon: Activity },
  { href: "/regions", label: "Region Atlas", Icon: Globe },
  { href: "/jjscan", label: "JJSCAN+", Icon: Scan },
  { href: "/abend", label: "ABEND Archaeologist", Icon: Bug },
  { href: "/confidence", label: "Confidence Score", Icon: Gauge },
  { href: "/review", label: "Review Queue", Icon: Inbox },
  { href: "/runbooks", label: "Runbooks", Icon: BookOpen },
  { href: "/audit", label: "Audit Log", Icon: FileText },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside
      className="hidden w-60 shrink-0 border-r border-border bg-bg-subtle md:block"
      data-print-hidden="true"
    >
      <ul className="sticky top-0 flex flex-col gap-1 p-3">
        {NAV.map(({ href, label, Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <li key={href}>
              <Link
                href={href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                  active
                    ? "bg-accent text-accent-fg"
                    : "text-fg-muted hover:bg-bg-elev hover:text-fg",
                )}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
