import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MessagesSquare,
  Users,
  Package,
  Bot,
  TrendingUp,
  ArrowRight,
  Zap,
  ArrowUpRight,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { Card, Chip, Skeleton, stagger, rise } from "../components/Primitives.jsx";
import { api } from "../api.js";
import { INTENT_META, EVENT_META, timeAgo, classNames } from "../lib/ui.js";
import { useCountUp } from "../lib/useCountUp.js";

function Sparkline({ data, color = "#10b981" }) {
  if (!data || data.length < 2) return null;
  const w = 96;
  const h = 30;
  const max = Math.max(1, ...data);
  const step = w / (data.length - 1);
  const pts = data.map((v, i) => `${i * step},${h - (v / max) * (h - 4) - 2}`);
  const line = `M ${pts.join(" L ")}`;
  const area = `${line} L ${w},${h} L 0,${h} Z`;
  const id = `spark-${color.replace("#", "")}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-8 w-24 overflow-visible">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StatCard({ icon: Icon, label, value, gradient, iconColor, spark, sparkColor, trend }) {
  const animated = useCountUp(value);
  return (
    <motion.div
      variants={rise}
      whileHover={{ y: -5, transition: { type: "spring", stiffness: 400, damping: 22 } }}
      className="group relative cursor-default overflow-hidden rounded-2xl bg-white/85 p-5 shadow-card ring-1 ring-slate-200/70 backdrop-blur-sm transition-shadow duration-200 hover:shadow-soft hover:ring-brand-300/60"
    >
      <div className={classNames("pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full opacity-60 blur-2xl transition-opacity group-hover:opacity-100", gradient)} />
      <div className="relative flex items-center justify-between">
        <div className={classNames("flex h-11 w-11 items-center justify-center rounded-xl shadow-sm", iconColor)}>
          <Icon className="h-5 w-5" />
        </div>
        {trend && (
          <Chip className="bg-brand-50 text-brand-700 ring-brand-600/20">
            <ArrowUpRight className="h-3 w-3" /> {trend}
          </Chip>
        )}
      </div>
      <div className="relative mt-4 flex items-end justify-between">
        <div>
          <p className="text-3xl font-extrabold tracking-tight text-slate-900">{animated}</p>
          <p className="mt-1 text-sm font-medium text-slate-500">{label}</p>
        </div>
        {spark && <Sparkline data={spark} color={sparkColor} />}
      </div>
    </motion.div>
  );
}

function Gauge({ value }) {
  const animated = useCountUp(value, { duration: 1100, decimals: 0 });
  const r = 42;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, animated));
  return (
    <div className="flex flex-col items-center">
      <div className="relative h-36 w-36">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <defs>
            <linearGradient id="gauge" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#34d399" />
              <stop offset="100%" stopColor="#059669" />
            </linearGradient>
          </defs>
          <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="11" />
          <circle
            cx="50"
            cy="50"
            r={r}
            fill="none"
            stroke="url(#gauge)"
            strokeWidth="11"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c - (pct / 100) * c}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-extrabold text-white">{Math.round(animated)}%</span>
          <span className="text-[11px] font-medium text-emerald-100/70">auto-resolved</span>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard({ info }) {
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.dashboard().then(setStats).catch((e) => setError(e.message));
    api.activity(10).then(setActivity).catch(() => setActivity([]));
  }, []);

  async function triggerAutomation() {
    setRunning(true);
    try {
      await api.runAutomation(6);
      setActivity(await api.activity(10));
      api.dashboard().then(setStats).catch(() => {});
    } finally {
      setRunning(false);
    }
  }

  if (error) {
    return <div className="p-6 text-sm text-rose-600">Failed to load dashboard: {error}</div>;
  }

  const inboundSpark = stats?.daily_volume.map((d) => d.inbound) || [];
  const outboundSpark = stats?.daily_volume.map((d) => d.outbound) || [];
  const chartData =
    stats?.daily_volume.map((d) => ({
      day: new Date(d.date).toLocaleDateString([], { weekday: "short" }),
      Inbound: d.inbound,
      Replies: d.outbound,
    })) || [];
  const maxIntent = Math.max(1, ...(stats?.intents.map((i) => i.count) || [1]));

  return (
    <div className="h-full overflow-y-auto">
      <div className="space-y-6 p-6">
        {/* Hero banner */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950 p-6 text-white shadow-soft sm:p-8"
        >
          <div className="pointer-events-none absolute -right-10 -top-16 h-52 w-52 rounded-full bg-brand-500/30 blur-3xl" />
          <div className="pointer-events-none absolute bottom-0 left-1/3 h-40 w-40 rounded-full bg-indigo-500/20 blur-3xl" />
          <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-brand-300">Welcome back 👋</p>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-brand-200 ring-1 ring-inset ring-white/15">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-400 opacity-75" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-brand-400" />
                  </span>
                  Live
                </span>
              </div>
              <h2 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-3xl">
                {stats ? `${stats.ai_resolution_rate}% handled automatically` : "Loading insights…"}
              </h2>
              <p className="mt-1 max-w-md text-sm text-slate-300">
                Your assistant resolved the vast majority of chats without a human — freeing your team for what matters.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link to="/chat">
                  <span className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-100">
                    <MessagesSquare className="h-4 w-4 text-brand-600" /> Try Live Chat
                  </span>
                </Link>
                <Link to="/inbox">
                  <span className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2 text-sm font-semibold text-white ring-1 ring-white/20 transition hover:bg-white/20">
                    Open Inbox <ArrowRight className="h-4 w-4" />
                  </span>
                </Link>
              </div>
            </div>
            <div className="shrink-0 rounded-2xl bg-white/5 p-2 ring-1 ring-white/10 backdrop-blur">
              {stats ? <Gauge value={stats.ai_resolution_rate} /> : <div className="h-36 w-36" />}
            </div>
          </div>
        </motion.div>

        {/* Stat cards */}
        {!stats ? (
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
        ) : (
          <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <StatCard
              icon={MessagesSquare}
              label="Conversations"
              value={stats.total_conversations}
              iconColor="bg-brand-100 text-brand-600"
              gradient="bg-brand-400/40"
              spark={inboundSpark}
              sparkColor="#10b981"
              trend={`${stats.open_conversations} open`}
            />
            <StatCard
              icon={Bot}
              label="Messages handled"
              value={stats.total_messages}
              iconColor="bg-violet-100 text-violet-600"
              gradient="bg-violet-400/40"
              spark={outboundSpark}
              sparkColor="#8b5cf6"
            />
            <StatCard
              icon={Users}
              label="Customers"
              value={stats.total_customers}
              iconColor="bg-sky-100 text-sky-600"
              gradient="bg-sky-400/40"
            />
            <StatCard
              icon={Package}
              label="Orders"
              value={stats.total_orders}
              iconColor="bg-amber-100 text-amber-600"
              gradient="bg-amber-400/40"
            />
          </motion.div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Volume chart */}
          <Card className="p-5 lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="font-bold text-slate-900">Message volume</h2>
                <p className="text-sm text-slate-500">Inbound vs AI replies · last 7 days</p>
              </div>
              <div className="flex items-center gap-3 text-xs font-medium text-slate-500">
                <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-brand-500" /> Inbound</span>
                <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-violet-500" /> Replies</span>
                <TrendingUp className="h-4 w-4 text-brand-500" />
              </div>
            </div>
            <div className="h-64">
              {stats && (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ left: -22, right: 8, top: 8 }}>
                    <defs>
                      <linearGradient id="gIn" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="gOut" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.28} />
                        <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
                    <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#94a3b8" }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#94a3b8" }} allowDecimals={false} width={38} />
                    <Tooltip
                      cursor={{ stroke: "#cbd5e1", strokeDasharray: 4 }}
                      contentStyle={{
                        borderRadius: 14,
                        border: "1px solid #e2e8f0",
                        boxShadow: "0 12px 40px -12px rgba(15,23,42,0.25)",
                        fontSize: 13,
                      }}
                    />
                    <Area type="monotone" dataKey="Inbound" stroke="#10b981" strokeWidth={2.5} fill="url(#gIn)" animationDuration={900} />
                    <Area type="monotone" dataKey="Replies" stroke="#8b5cf6" strokeWidth={2.5} fill="url(#gOut)" animationDuration={900} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          {/* Intent breakdown */}
          <Card className="p-5">
            <h2 className="mb-4 font-bold text-slate-900">Top intents</h2>
            <div className="space-y-3.5">
              {stats?.intents.length === 0 && <p className="text-sm text-slate-400">No messages yet.</p>}
              {stats?.intents.map((i, idx) => {
                const meta = INTENT_META[i.intent] || INTENT_META.unknown;
                return (
                  <div key={i.intent}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-600">{meta.emoji} {meta.label}</span>
                      <span className="font-bold text-slate-800">{i.count}</span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(i.count / maxIntent) * 100}%` }}
                        transition={{ delay: 0.1 + idx * 0.08, duration: 0.7, ease: "easeOut" }}
                        className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-5 flex items-center justify-between rounded-xl bg-gradient-to-r from-amber-50 to-white px-4 py-3 ring-1 ring-amber-100">
              <div className="flex items-center gap-2 text-sm font-medium text-amber-700">
                <Zap className="h-4 w-4" /> Avg. confidence
              </div>
              <span className="text-lg font-extrabold text-slate-900">{stats?.avg_confidence ?? 0}%</span>
            </div>
          </Card>
        </div>

        {/* Top FAQs */}
        <Card className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-bold text-slate-900">Most-asked questions</h2>
            <Link to="/faqs" className="flex items-center gap-1 text-sm font-semibold text-brand-600 hover:text-brand-700">
              Manage <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {stats?.top_faqs.map((f, idx) => (
              <div key={idx} className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-200 hover:translate-x-1 hover:bg-slate-50">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-slate-100 to-slate-200 text-xs font-bold text-slate-500 transition-colors group-hover:from-brand-100 group-hover:to-brand-200">
                  {idx + 1}
                </span>
                <span className="flex-1 truncate text-sm font-medium text-slate-700">{f.question}</span>
                <Chip className="bg-slate-100 text-slate-600 ring-slate-500/20">{f.hits} hits</Chip>
              </div>
            ))}
          </div>
        </Card>

        {/* Recent activity — audit trail of actions the AI performed */}
        <Card className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-bold text-slate-900">Recent activity</h2>
              <p className="text-sm text-slate-500">Cancellations, returns, refunds & proactive updates the AI processed — logged live.</p>
            </div>
            <button
              onClick={triggerAutomation}
              disabled={running}
              title="Advance orders now & notify customers"
              className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
            >
              <Zap className="h-3.5 w-3.5" /> {running ? "Running…" : "Run automation"}
            </button>
          </div>
          <div className="space-y-1">
            {activity.length === 0 && <p className="py-4 text-center text-sm text-slate-400">No actions yet — cancel or return an order in Live Chat.</p>}
            {activity.map((e) => {
              const meta = EVENT_META[e.event_type] || { emoji: "•", label: e.event_type, chip: "bg-slate-100 text-slate-600 ring-slate-500/20" };
              return (
                <div key={e.id} className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-slate-50">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-base">{meta.emoji}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-slate-700">
                      <span className="font-mono font-semibold text-slate-900">{e.order_number}</span>
                      {e.customer_name && <span className="text-slate-400"> · {e.customer_name}</span>}
                      {e.reason && <span className="text-slate-500"> — {e.reason}</span>}
                    </p>
                  </div>
                  <Chip className={meta.chip}>{meta.label}</Chip>
                  <span className="w-14 shrink-0 text-right text-[11px] text-slate-400">{timeAgo(e.created_at)}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
