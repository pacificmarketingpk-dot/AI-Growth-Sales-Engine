import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { AppLayout } from "./layouts/AppLayout";
import { Spinner, ToastProvider } from "./components/ui";
import Login from "./pages/Login";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Prospects = lazy(() => import("./pages/Prospects"));
const ProspectDetailPage = lazy(() => import("./pages/ProspectDetail"));
const Analysis = lazy(() => import("./pages/Analysis"));
const HotLeads = lazy(() => import("./pages/HotLeads"));
const Conversations = lazy(() => import("./pages/Conversations"));
const OutreachPage = lazy(() => import("./pages/Outreach"));
const Meetings = lazy(() => import("./pages/Meetings"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const Analytics = lazy(() => import("./pages/Analytics"));
const SettingsPage = lazy(() => import("./pages/Settings"));

function Gate() {
  const { user, ready } = useAuth();
  if (!ready) return <Spinner />;
  if (!user) return <Login />;
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="prospects" element={<Prospects />} />
          <Route path="prospects/:id" element={<ProspectDetailPage />} />
          <Route path="analysis" element={<Analysis />} />
          <Route path="hot-leads" element={<HotLeads />} />
          <Route path="conversations" element={<Conversations />} />
          <Route path="outreach" element={<OutreachPage />} />
          <Route path="meetings" element={<Meetings />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider><AuthProvider><Gate /></AuthProvider></ToastProvider>
    </BrowserRouter>
  );
}
