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
  const token = localStorage.getItem("token");

  // Not properly authenticated
  if (!isLoggedIn || !token) {
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("role");
    localStorage.removeItem("name");
    localStorage.removeItem("token");

    return <Navigate to="/login" replace />;
  }

  // Invalid stored role
  if (
    role !== "victim" &&
    role !== "authority" &&
    role !== "counsellor"
  ) {
    localStorage.clear();
    return <Navigate to="/login" replace />;
  }

  // Logged in, but trying to access another role's dashboard
  if (role !== allowedRole) {
    return <Navigate to={`/${role}`} replace />;
  }

  return children;
}

export default ProtectedRoute;