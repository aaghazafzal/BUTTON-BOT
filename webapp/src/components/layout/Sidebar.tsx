"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, PlusCircle, Settings, Box, Sparkles } from "lucide-react";
import { ThemeToggle } from "@/components/theme/ThemeToggle";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/create", label: "Create Post", icon: PlusCircle },
  { href: "/projects", label: "Auto Adders", icon: Box },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex flex-col w-72 h-screen border-r border-border glass fixed left-0 top-0 z-50">
      <div className="p-8 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="bg-primary text-primary-foreground p-2 rounded-xl">
            <Sparkles className="w-5 h-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">Univora</h1>
        </div>
        <ThemeToggle />
      </div>

      <div className="px-6 pb-2">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Menu</p>
      </div>

      <nav className="flex-1 px-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                isActive
                  ? "bg-primary text-primary-foreground font-medium shadow-md shadow-primary/10 translate-x-1"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground hover:translate-x-1"
              }`}
            >
              <Icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
