"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Live Feed" },
  { href: "/alerts", label: "Alerts" },
  { href: "/config", label: "Config" },
  { href: "/sources", label: "Sources" },
  { href: "/stats", label: "Stats" },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-20 border-b border-ink-700 bg-ink-900/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-5 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span aria-hidden>🛢️</span>
          <span>Oil News Alert</span>
        </Link>
        <nav className="flex gap-1">
          {LINKS.map((l) => {
            const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-md px-3 py-1.5 text-sm transition ${
                  active
                    ? "bg-ink-700 text-white"
                    : "text-slate-400 hover:bg-ink-800 hover:text-slate-200"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto hidden text-xs text-slate-500 sm:block">
          decision-support · human in the loop
        </div>
      </div>
    </header>
  );
}
