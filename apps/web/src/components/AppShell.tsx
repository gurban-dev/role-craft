"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { logoutRequest } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/Toast";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/applications", label: "Applications" },
  { href: "/contacts", label: "Contacts" },
  { href: "/resumes", label: "Resumes" },
  { href: "/research", label: "Research" },
  { href: "/runs", label: "Runs" },
  { href: "/settings", label: "Settings" },
  { href: "/profile", label: "Profile" },
  { href: "/dev", label: "Dev" },
] as const;

type AppShellProps = {
  userName?: string;
  userEmail?: string;
  children: React.ReactNode;
};

export function AppShell({ userName, userEmail, children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const toast = useToast();
  const [loggingOut, setLoggingOut] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logoutRequest();
      toast.info("Signed out");
      router.replace("/login");
      router.refresh();
    } catch (err) {
      toast.error("Logout failed", err instanceof Error ? err.message : undefined);
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <div className="flex min-h-screen">
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-30 w-60 border-r border-[var(--border)] bg-[var(--surface)] transition-transform lg:static lg:translate-x-0",
            navOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="flex h-14 items-center border-b border-[var(--border)] px-4">
            <Link href="/dashboard" className="font-serif text-lg font-semibold tracking-tight">
              ApplyDesk
            </Link>
          </div>
          <nav className="flex flex-col gap-0.5 p-2" aria-label="Primary">
            {navItems.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setNavOpen(false)}
                  className={cn(
                    "rounded px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                      : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>

        {navOpen ? (
          <button
            type="button"
            className="fixed inset-0 z-20 bg-slate-950/40 lg:hidden"
            aria-label="Close navigation"
            onClick={() => setNavOpen(false)}
          />
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-[var(--border)] bg-[var(--surface)]/95 px-4 backdrop-blur">
            <button
              type="button"
              className="btn-secondary lg:hidden"
              onClick={() => setNavOpen(true)}
              aria-expanded={navOpen}
              aria-controls="primary-nav"
            >
              Menu
            </button>
            <div className="hidden text-sm text-[var(--muted)] lg:block">
              Application pipeline console
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right text-xs leading-tight">
                <div className="font-medium text-[var(--fg)]">{userName ?? "User"}</div>
                <div className="text-[var(--muted)]">{userEmail}</div>
              </div>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleLogout}
                disabled={loggingOut}
              >
                {loggingOut ? "Signing out…" : "Sign out"}
              </button>
            </div>
          </header>
          <main id="main" className="flex-1 px-4 py-5 sm:px-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
