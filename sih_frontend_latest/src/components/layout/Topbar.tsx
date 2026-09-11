import {Link, useNavigate} from "react-router-dom";
import {navSections,counsellorNavSections,victimNavSections} from "../../../data/mockData";
import { useEffect, useState } from "react";


import { Bell, Moon, Search, Sun } from "lucide-react";

import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { Separator } from "../ui/separator";

export function Topbar() {
  const navigate=useNavigate();
  const role=localStorage.getItem("role");
  const nav=(role==="authority"?navSections:role==="counsellor"?counsellorNavSections:victimNavSections).flatMap(s=>s.items);
  const [isDark, setIsDark] = useState(false);


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

  if (localStorage.getItem("role") === "counsellor") {
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

if (localStorage.getItem("role") === "victim") {
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
      <Link to={`/${role}`} className="font-bold text-primary">SAHAS</Link>
      <select aria-label="Navigate" defaultValue="" onChange={e=>{if(e.target.value)navigate(e.target.value);e.target.value='';}} className="max-w-36 rounded border bg-card p-2 text-sm lg:hidden"><option value="">Menu</option>{nav.map(i=><option value={i.path} key={i.path}>{i.label}</option>)}</select>
      {role!=="victim"&&<form className="relative hidden w-full max-w-sm md:block" onSubmit={e=>{e.preventDefault();const value=String(new FormData(e.currentTarget).get('case')||'').trim();if(value)navigate(`/cases/${encodeURIComponent(value)}`);}}><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"/><Input name="case" aria-label="Open case by ID" placeholder="Enter case ID and press Enter" className="pl-9"/></form>}

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Notifications"
          onClick={()=>navigate(role==="victim"?"/victim":"/alerts")}
          className="relative"
        >
          <Bell className="h-4 w-4" />

        </Button>

        <Button
          variant="ghost"
          size="icon"
          aria-label="Toggle theme"
          onClick={() => setIsDark((prev) => !prev)}
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <Button variant="ghost" size="sm" onClick={()=>navigate("/settings")}>Account</Button>
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