import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  MessagesSquare,
  Inbox,
  Package,
  BookOpen,
  Wallet,
  Bot,
  Sparkles,
  LogOut,
} from "lucide-react";
import { classNames } from "../lib/ui.js";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/chat", label: "Live Chat", icon: MessagesSquare },
  { to: "/inbox", label: "Inbox", icon: Inbox },
  { to: "/orders", label: "Orders", icon: Package },
  { to: "/refunds", label: "Refunds", icon: Wallet },
  { to: "/faqs", label: "Knowledge Base", icon: BookOpen },
];

export default function Sidebar({ info, onLogout }) {
  return (
    <aside className="relative hidden w-64 shrink-0 flex-col overflow-hidden bg-gradient-to-b from-slate-900 via-slate-900 to-emerald-950 text-slate-300 lg:flex">
      {/* Ambient glows — same emerald + indigo depth as the dashboard hero */}
      <div className="pointer-events-none absolute -right-12 -top-16 h-56 w-56 rounded-full bg-brand-500/25 blur-3xl" />
      <div className="pointer-events-none absolute bottom-24 -left-16 h-52 w-52 rounded-full bg-indigo-500/20 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_55%_at_50%_0%,rgba(255,255,255,0.06),transparent_60%)]" />

      {/* Brand header */}
      <div className="relative flex items-center gap-3 px-6 py-6">
        <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 shadow-glow">
          <Bot className="h-6 w-6 text-white" />
          <span className="absolute -right-0.5 -top-0.5 flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-300 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-brand-400 ring-2 ring-slate-900" />
          </span>
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-white">{info?.business_name || "Aurora"}</p>
          <p className="text-xs text-slate-400">AI Support Suite</p>
        </div>
      </div>

      <nav className="relative mt-1 flex-1 space-y-1 px-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className="block">
            {({ isActive }) => (
              <div
                className={classNames(
                  "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "text-white"
                    : "text-slate-400 hover:translate-x-1 hover:bg-white/5 hover:text-white"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="nav-active"
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-brand-500/25 to-brand-500/5 ring-1 ring-brand-400/30"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                {isActive && (
                  <motion.span
                    layoutId="nav-bar"
                    className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-brand-400"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <Icon
                  className={classNames(
                    "relative z-10 h-5 w-5 transition-all duration-200",
                    isActive ? "text-brand-300" : "text-slate-500 group-hover:scale-110 group-hover:text-slate-300"
                  )}
                />
                <span className="relative z-10">{label}</span>
              </div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* AI engine status */}
      <div className="relative m-3 overflow-hidden rounded-2xl bg-white/5 p-4 ring-1 ring-white/10 backdrop-blur">
        <div className="pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full bg-brand-500/20 blur-2xl" />
        <div className="relative flex items-center gap-2 text-brand-300">
          <Sparkles className="h-4 w-4" />
          <span className="text-[11px] font-semibold uppercase tracking-widest">AI Engine</span>
        </div>
        <p className="relative mt-2 text-sm font-semibold capitalize text-white">
          {info?.ai_provider || "mock"} · online
        </p>
        <div className="relative mt-3 flex items-center gap-2">
          <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
            <span className="block h-full w-4/5 rounded-full bg-gradient-to-r from-brand-400 to-brand-500" />
          </span>
          <span className="text-[11px] text-slate-400">WA · {info?.whatsapp_provider || "mock"}</span>
        </div>
      </div>

      {/* Sign out */}
      <div className="relative px-3 pb-4">
        <button
          onClick={onLogout}
          className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-400 transition-all duration-200 hover:bg-rose-500/10 hover:text-rose-300"
        >
          <LogOut className="h-5 w-5 text-slate-500 transition-colors group-hover:text-rose-400" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
