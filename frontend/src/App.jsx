import { useEffect, useState } from "react";
import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { LayoutDashboard, MessagesSquare, Inbox, Package, BookOpen, Wallet } from "lucide-react";
import Sidebar from "./components/Sidebar.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import LiveChat from "./pages/LiveChat.jsx";
import InboxPage from "./pages/InboxPage.jsx";
import Orders from "./pages/Orders.jsx";
import Refunds from "./pages/Refunds.jsx";
import FAQs from "./pages/FAQs.jsx";
import Login from "./pages/Login.jsx";
import { api, getToken } from "./api.js";
import { classNames } from "./lib/ui.js";
import { Spinner } from "./components/Primitives.jsx";

const MOBILE_NAV = [
  { to: "/", label: "Home", icon: LayoutDashboard, end: true },
  { to: "/chat", label: "Chat", icon: MessagesSquare },
  { to: "/inbox", label: "Inbox", icon: Inbox },
  { to: "/orders", label: "Orders", icon: Package },
  { to: "/refunds", label: "Refunds", icon: Wallet },
];

function Page({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      className="h-full"
    >
      {children}
    </motion.div>
  );
}

export default function App() {
  const [info, setInfo] = useState(null);
  // auth: null = checking, false = show login, true = show app
  const [authed, setAuthed] = useState(null);
  const location = useLocation();

  // Public — the login screen shows the business name too.
  useEffect(() => {
    api.systemInfo().then(setInfo).catch(() => setInfo(null));
  }, []);

  // On load, verify any stored token; listen for expiry/logout events.
  useEffect(() => {
    if (!getToken()) {
      setAuthed(false);
      return;
    }
    api.me().then(() => setAuthed(true)).catch(() => setAuthed(false));
  }, []);

  useEffect(() => {
    const onLogout = () => setAuthed(false);
    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, []);

  if (authed === null) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-900">
        <Spinner className="h-8 w-8 text-brand-400" />
      </div>
    );
  }

  if (!authed) {
    return <Login info={info} onSuccess={() => setAuthed(true)} />;
  }

  return (
    <div className="flex h-full">
      <Sidebar info={info} onLogout={() => api.logout()} />

      <div className="flex min-w-0 flex-1 flex-col">
        <main className="flex-1 overflow-hidden">
          <AnimatePresence mode="wait">
            <Routes location={location} key={location.pathname}>
              <Route path="/" element={<Page><Dashboard info={info} /></Page>} />
              <Route path="/chat" element={<Page><LiveChat info={info} /></Page>} />
              <Route path="/inbox" element={<Page><InboxPage /></Page>} />
              <Route path="/orders" element={<Page><Orders /></Page>} />
              <Route path="/refunds" element={<Page><Refunds /></Page>} />
              <Route path="/faqs" element={<Page><FAQs /></Page>} />
            </Routes>
          </AnimatePresence>
        </main>

        {/* Mobile bottom nav */}
        <nav className="grid grid-cols-5 border-t border-slate-200 bg-white/90 backdrop-blur lg:hidden">
          {MOBILE_NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                classNames(
                  "flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium transition-colors",
                  isActive ? "text-brand-600" : "text-slate-400"
                )
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
