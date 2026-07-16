import { useState } from "react";
import { motion } from "framer-motion";
import {
  Bot,
  Lock,
  User,
  Eye,
  EyeOff,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Globe,
  Camera,
  Zap,
} from "lucide-react";
import { api } from "../api.js";
import { Spinner } from "../components/Primitives.jsx";

const FEATURES = [
  {
    icon: Sparkles,
    title: "Autonomous AI agent",
    text: "Cancels, returns & refunds orders end-to-end — on its own.",
  },
  {
    icon: Globe,
    title: "Speaks 20+ languages",
    text: "Replies in each customer's own language & script.",
  },
  {
    icon: Camera,
    title: "Vision damage checks",
    text: "Inspects product photos and auto-approves genuine returns.",
  },
  {
    icon: Zap,
    title: "Always on · instant",
    text: "24/7 answers in under a second — no human needed.",
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.15 } },
};
const item = {
  hidden: { opacity: 0, x: -16 },
  show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 240, damping: 24 } },
};

export default function Login({ info, onSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const business = info?.business_name || "WhatsApp Customer Service";
  const tagline = info?.business_tagline || "Premium lifestyle & electronics";

  async function submit(e) {
    e.preventDefault();
    if (busy) return;
    setError("");
    setBusy(true);
    try {
      await api.login(username.trim(), password);
      onSuccess?.();
    } catch (err) {
      setError(err.message || "Login failed. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen w-full overflow-hidden bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950 text-white">
      {/* Ambient glows */}
      <div className="pointer-events-none absolute -left-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-brand-500/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 right-0 h-[30rem] w-[30rem] rounded-full bg-indigo-500/20 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_60%_at_50%_-10%,rgba(255,255,255,0.05),transparent_60%)]" />

      {/* ─────────── LEFT · brand showcase (large screens) ─────────── */}
      <motion.aside
        variants={container}
        initial="hidden"
        animate="show"
        className="relative hidden w-1/2 flex-col justify-between overflow-hidden p-12 xl:p-16 lg:flex"
      >
        {/* Brand */}
        <motion.div variants={item} className="flex items-center gap-3">
          <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 shadow-glow">
            <Bot className="h-7 w-7 text-white" />
            <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-300 opacity-75" />
              <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-brand-400 ring-2 ring-slate-900" />
            </span>
          </div>
          <div>
            <p className="text-base font-bold tracking-tight text-white">{business}</p>
            <p className="text-xs text-slate-400">{tagline}</p>
          </div>
        </motion.div>

        {/* Headline + features */}
        <div className="max-w-md">
          <motion.div
            variants={item}
            className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-widest text-brand-300 ring-1 ring-white/10"
          >
            <Sparkles className="h-3.5 w-3.5" /> AI Support Suite
          </motion.div>
          <motion.h1
            variants={item}
            className="text-3xl font-bold leading-tight tracking-tight text-white xl:text-4xl"
          >
            Customer support that
            <span className="bg-gradient-to-r from-brand-300 to-emerald-200 bg-clip-text text-transparent">
              {" "}runs itself.
            </span>
          </motion.h1>
          <motion.p variants={item} className="mt-3 text-sm leading-relaxed text-slate-400">
            An agentic WhatsApp assistant that understands, decides and acts —
            so your team only handles what truly needs a human.
          </motion.p>

          <motion.ul variants={container} className="mt-8 space-y-4">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <motion.li key={title} variants={item} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-500/15 text-brand-300 ring-1 ring-brand-400/20">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-sm font-semibold text-white">{title}</p>
                  <p className="text-xs text-slate-400">{text}</p>
                </div>
              </motion.li>
            ))}
          </motion.ul>
        </div>

        {/* Stat strip */}
        <motion.div
          variants={item}
          className="flex items-center gap-6 rounded-2xl bg-white/5 px-6 py-4 ring-1 ring-white/10 backdrop-blur"
        >
          {[
            ["1,000", "orders"],
            ["20+", "languages"],
            ["62%", "auto-resolved"],
          ].map(([n, l]) => (
            <div key={l} className="flex flex-col">
              <span className="text-xl font-bold text-white">{n}</span>
              <span className="text-[11px] uppercase tracking-wider text-slate-400">{l}</span>
            </div>
          ))}
        </motion.div>
      </motion.aside>

      {/* Divider glow between the panels */}
      <div className="pointer-events-none absolute inset-y-0 left-1/2 hidden w-px bg-gradient-to-b from-transparent via-white/10 to-transparent lg:block" />

      {/* ─────────── RIGHT · sign-in form ─────────── */}
      <div className="relative flex w-full items-center justify-center p-6 sm:p-10 lg:w-1/2">
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-sm"
        >
          {/* Compact brand for mobile (left panel is hidden there) */}
          <div className="mb-8 flex flex-col items-center text-center lg:hidden">
            <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 shadow-glow">
              <Bot className="h-7 w-7 text-white" />
            </div>
            <h1 className="mt-4 text-lg font-bold tracking-tight text-white">{business}</h1>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl font-bold tracking-tight text-white">Welcome back 👋</h2>
            <p className="mt-1 text-sm text-slate-400">Sign in to your admin dashboard.</p>
          </div>

          <form
            onSubmit={submit}
            className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-xl sm:p-7"
          >
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              Username
            </label>
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-white/10 bg-slate-900/40 px-3 focus-within:border-brand-400/60 focus-within:ring-2 focus-within:ring-brand-400/20">
              <User className="h-4 w-4 shrink-0 text-slate-500" />
              <input
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                autoComplete="username"
                className="w-full bg-transparent py-2.5 text-sm text-white placeholder-slate-500 outline-none"
              />
            </div>

            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              Password
            </label>
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-900/40 px-3 focus-within:border-brand-400/60 focus-within:ring-2 focus-within:ring-brand-400/20">
              <Lock className="h-4 w-4 shrink-0 text-slate-500" />
              <input
                type={show ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                className="w-full bg-transparent py-2.5 text-sm text-white placeholder-slate-500 outline-none"
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="shrink-0 text-slate-500 transition-colors hover:text-slate-300"
                tabIndex={-1}
                aria-label={show ? "Hide password" : "Show password"}
              >
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-3 rounded-lg bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-300 ring-1 ring-rose-500/20"
              >
                {error}
              </motion.p>
            )}

            <button
              type="submit"
              disabled={busy || !username || !password}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-brand-500 to-brand-600 py-3 text-sm font-semibold text-white shadow-lg transition-all duration-200 hover:from-brand-500 hover:to-brand-700 hover:shadow-glow active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
            >
              {busy ? (
                <>
                  <Spinner className="h-4 w-4 text-white" /> Signing in…
                </>
              ) : (
                <>
                  Sign in to dashboard <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>

            <p className="mt-5 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
              <ShieldCheck className="h-3.5 w-3.5" /> Protected by an encrypted session token
            </p>
          </form>

          <p className="mt-6 text-center text-[11px] text-slate-500">
            © {business} · Admin portal
          </p>
        </motion.div>
      </div>
    </div>
  );
}
