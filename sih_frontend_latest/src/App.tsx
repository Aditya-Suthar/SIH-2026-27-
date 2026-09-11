import Home from "./pages/Home"
import Login from "./pages/Login"
import { Route, Routes } from "react-router-dom";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import AuthorityDashboard from "../pages/AuthorityDashboard";
import {Alerts,Counsellors,Analytics,Reports,Settings} from "./pages/Operations";
import VictimDashboard from "../pages/VictimDashboard";
import CounsellorDashboard from "../pages/CounsellorDashboard";
import ProtectedRoute from "./components/ProtectedRoute";
import Cases from "./pages/Cases";
import CaseDetails from "./pages/CaseDetails";
import CounsellorMessages from "./pages/CounsellorMessages";
import Sessions from "./pages/Sessions";
import Resources from "./pages/Resources";


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

      <Route path="/cases/:caseId" element={<CaseDetails />} />

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

<Route
  path="/counsellor/messages"
  element={
    <ProtectedRoute allowedRole="counsellor">
      <CounsellorMessages />
    </ProtectedRoute>
  }
/>

<Route path="/cases" element={<Cases />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/counsellors" element={<Counsellors />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/resources" element={<Resources />} />
      </Route>
    <Route path="*" element={<Home />} />
    </Routes>
  )
}

export default App