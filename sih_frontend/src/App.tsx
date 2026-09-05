import Home from "./pages/Home"
import Login from "./pages/Login"
import { Route, Routes } from "react-router-dom";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import AuthorityDashboard from "../pages/AuthorityDashboard";
import ComingSoon from "../pages/ComingSoon";
import VictimDashboard from "../pages/VictimDashboard";
import CounsellorDashboard from "../pages/CounsellorDashboard";
import ProtectedRoute from "./components/ProtectedRoute";
import Cases from "./pages/Cases";


function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />

      

      <Route element={<DashboardLayout />}>
        <Route
  path="/victim"
  element={
    <ProtectedRoute allowedRole="victim">
      <VictimDashboard />
    </ProtectedRoute>
  }
/>

              <Route
        path="/authority"
        element={
          <ProtectedRoute allowedRole="authority">
  <AuthorityDashboard />
</ProtectedRoute>
        }
      />

      <Route
        path="/counsellor"
        element={
         <ProtectedRoute allowedRole="counsellor">
      <CounsellorDashboard />
    </ProtectedRoute>
        }
      />

<Route path="/cases" element={<Cases />} />
        <Route path="/alerts" element={<ComingSoon section="Alerts" />} />
        <Route path="/counsellors" element={<ComingSoon section="Counsellors" />} />
        <Route path="/sessions" element={<ComingSoon section="Sessions" />} />
        <Route path="/analytics" element={<ComingSoon section="Analytics" />} />
        <Route path="/reports" element={<ComingSoon section="Reports" />} />
        <Route path="/resources" element={<ComingSoon section="Resources" />} />
      </Route>
    </Routes>
  )
}

export default App