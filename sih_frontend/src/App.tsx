import Home from "./pages/Home"
import Login from "./pages/Login"
import { Navigate, Route, Routes } from "react-router-dom";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import AuthorityDashboard from "../pages/AuthorityDashboard";
import ComingSoon from "../pages/ComingSoon";


function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route element={<DashboardLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<AuthorityDashboard />} />
        <Route path="/cases" element={<ComingSoon section="Cases" />} />
        <Route path="/alerts" element={<ComingSoon section="Alerts" />} />
        <Route path="/counsellors" element={<ComingSoon section="Counsellors" />} />
        <Route path="/sessions" element={<ComingSoon section="Sessions" />} />
        <Route path="/analytics" element={<ComingSoon section="Analytics" />} />
        <Route path="/reports" element={<ComingSoon section="Reports" />} />
        <Route path="/resources" element={<ComingSoon section="Resources" />} />
        <Route path="/settings" element={<ComingSoon section="Settings" />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}

export default App