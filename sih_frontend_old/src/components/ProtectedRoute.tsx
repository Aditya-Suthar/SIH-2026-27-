import { Navigate } from "react-router-dom";

function ProtectedRoute({
  children,
  allowedRole,
}: {
  children: React.ReactNode;
  allowedRole: "victim" | "authority" | "counsellor";
}) {
  const isLoggedIn = localStorage.getItem("isLoggedIn") === "true";
  const role = localStorage.getItem("role");
  const token = localStorage.getItem("access_token");

  if (!isLoggedIn || !token) {
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("role");
    localStorage.removeItem("name");
    localStorage.removeItem("access_token");

    return <Navigate to="/login" replace />;
  }

  if (
    role !== "victim" &&
    role !== "authority" &&
    role !== "counsellor"
  ) {
    localStorage.clear();
    return <Navigate to="/login" replace />;
  }

  if (role !== allowedRole) {
    return <Navigate to={`/${role}`} replace />;
  }

  return children;
}

export default ProtectedRoute;