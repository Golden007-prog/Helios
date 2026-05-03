"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";

export function TopNav() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const stored = (window.localStorage.getItem("helios_theme") as "light" | "dark") ?? "dark";
    setTheme(stored);
    document.documentElement.dataset.theme = stored;
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    window.localStorage.setItem("helios_theme", next);
  }

  return (
    <nav className="border-b border-border bg-bg-elev" data-print-hidden="true">
      <div className="container flex h-14 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="inline-block size-3 rounded-full bg-accent" aria-hidden />
          Helios
          <span className="text-xs font-normal text-fg-muted">control plane</span>
        </Link>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggle}
            aria-label="Toggle theme"
            className={cn(
              "flex size-8 items-center justify-center rounded-md border border-border",
              "hover:bg-bg-subtle",
            )}
          >
            {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
        </div>
      </div>
    </nav>
  );
}
