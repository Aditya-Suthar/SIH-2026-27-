import { Navigate, Outlet, useLocation } from "react-router-dom";

import { Sidebar } from "./Sidebar";

import { Topbar } from "./Topbar";

export function DashboardLayout() {
  const role=localStorage.getItem("role");
  const path=useLocation().pathname;
  if(!localStorage.getItem("access_token")||!["victim","counsellor","authority"].includes(role||""))return <Navigate to="/login" replace/>;
  if(role==="victim" && !["/victim","/sessions","/resources","/settings"].includes(path))return <Navigate to="/victim" replace/>;
  if(role!=="authority" && ["/authority","/counsellors"].includes(path))return <Navigate to={`/${role}`} replace/>;
  return (
    <div className="flex min-h-screen w-full bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
