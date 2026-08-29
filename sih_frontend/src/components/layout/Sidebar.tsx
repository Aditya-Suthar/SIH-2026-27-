import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  AlertTriangle,
  Users,
  CalendarClock,
  BarChart3,
  FileText,
  Library,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { navSections } from "../../../data/mockData";

import { cn } from "../../../lib/utils";

const iconMap = {
  LayoutDashboard,
  FolderKanban,
  AlertTriangle,
  Users,
  CalendarClock,
  BarChart3,
  FileText,
  Library,
  Settings,
} as const;

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card lg:flex">
      <div className="flex items-center gap-2.5 px-6 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <div>
          <p className="text-base font-bold leading-tight text-foreground">SAHAS</p>
          <p className="text-xs text-muted-foreground">Welfare Authority</p>
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 pb-6">
        {navSections.map((section) => (
          <div key={section.title}>
            <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {section.title}
            </p>
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = iconMap[item.icon as keyof typeof iconMap];
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
                        isActive && "bg-primary/10 text-primary hover:bg-primary/10 hover:text-primary"
                      )
                    }
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
