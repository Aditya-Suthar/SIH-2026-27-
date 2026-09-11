import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import { Bell, Moon, Search, Sun } from "lucide-react";

import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { Separator } from "../ui/separator";

export function Topbar() {
  const [isDark, setIsDark] = useState(false);
  const location = useLocation();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

const authorityName =
  localStorage.getItem("name") || "District Welfare Officer";

let user = {
  initials: authorityName
    .split(" ")
    .map((word) => word[0])
    .join("")
    .slice(0, 2)
    .toUpperCase(),

  name: authorityName,
  access: "Authority Access",
};

  if (location.pathname.startsWith("/counsellor")) {
  const name = localStorage.getItem("name") || "Counsellor";

  user = {
    initials: name
      .split(" ")
      .map((word) => word[0])
      .join("")
      .slice(0, 2)
      .toUpperCase(),

    name: name,
    access: "Counsellor Access",
  };
}

if (location.pathname.startsWith("/victim")) {
  const name = localStorage.getItem("name") || "Anonymous Survivor";

  user = {
    initials: name
      .split(" ")
      .map((word) => word[0])
      .join("")
      .slice(0, 2)
      .toUpperCase(),

    name: name,
    access: "Victim Access",
  };
}

  return (
    <header className="sticky top-0 z-10 flex items-center gap-4 border-b border-border bg-card/80 px-4 py-3 backdrop-blur sm:px-6">
      <div className="relative w-full max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search cases..." className="pl-9" />
      </div>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Notifications"
          className="relative"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          aria-label="Toggle theme"
          onClick={() => setIsDark((prev) => !prev)}
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <Separator orientation="vertical" className="mx-1 hidden h-8 sm:block" />

        <div className="flex items-center gap-2.5">
          <Avatar>
            <AvatarFallback>{user.initials}</AvatarFallback>
          </Avatar>

          <div className="hidden text-left sm:block">
            <p className="text-sm font-semibold leading-tight text-foreground">
              {user.name}
            </p>
            <p className="text-xs text-muted-foreground">{user.access}</p>
          </div>
        </div>
      </div>
    </header>
  );
}