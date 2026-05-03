import Link from "next/link";
import { ChevronRight } from "lucide-react";

export interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4 text-sm text-fg-muted">
      <ol className="flex items-center gap-1">
        {items.map((c, i) => {
          const last = i === items.length - 1;
          return (
            <li key={i} className="flex items-center gap-1">
              {c.href && !last ? (
                <Link href={c.href} className="hover:text-fg">
                  {c.label}
                </Link>
              ) : (
                <span className={last ? "text-fg" : ""}>{c.label}</span>
              )}
              {!last && <ChevronRight className="size-3" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
