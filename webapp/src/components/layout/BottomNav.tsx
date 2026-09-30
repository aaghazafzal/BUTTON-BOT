"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, PlusCircle, Settings, Box } from "lucide-react";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/create", label: "Create", icon: PlusCircle },
  { href: "/projects", label: "Projects", icon: Box },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 glass border-t border-border z-50 pb-safe">
      <div className="flex justify-around items-center h-20 px-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center justify-center w-full h-full gap-1.5 transition-all duration-200 ${
                isActive
                  ? "text-foreground font-medium -translate-y-1"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <div className={`p-2 rounded-full transition-colors ${isActive ? 'bg-primary/10 text-primary' : 'bg-transparent'}`}>
                <Icon className="w-6 h-6" strokeWidth={isActive ? 2.5 : 2} />
              </div>
              <span className="text-[10px] leading-none font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
