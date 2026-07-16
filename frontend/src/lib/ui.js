// Shared presentation helpers: status colours, labels, formatting.

export function classNames(...parts) {
  return parts.filter(Boolean).join(" ");
}

export const CONVO_STATUS = {
  open: { label: "AI handling", dot: "bg-brand-500", chip: "bg-brand-50 text-brand-700 ring-brand-600/20" },
  needs_human: { label: "Needs human", dot: "bg-amber-500", chip: "bg-amber-50 text-amber-700 ring-amber-600/20" },
  resolved: { label: "Resolved", dot: "bg-slate-400", chip: "bg-slate-100 text-slate-600 ring-slate-500/20" },
};

export const ORDER_STATUS = {
  pending: { label: "Pending", chip: "bg-slate-100 text-slate-600 ring-slate-500/20" },
  confirmed: { label: "Confirmed", chip: "bg-sky-50 text-sky-700 ring-sky-600/20" },
  packed: { label: "Packed", chip: "bg-indigo-50 text-indigo-700 ring-indigo-600/20" },
  shipped: { label: "Shipped", chip: "bg-violet-50 text-violet-700 ring-violet-600/20" },
  out_for_delivery: { label: "Out for delivery", chip: "bg-amber-50 text-amber-700 ring-amber-600/20" },
  delivered: { label: "Delivered", chip: "bg-brand-50 text-brand-700 ring-brand-600/20" },
  cancelled: { label: "Cancelled", chip: "bg-rose-50 text-rose-700 ring-rose-600/20" },
  returned: { label: "Returned", chip: "bg-orange-50 text-orange-700 ring-orange-600/20" },
};

export const INTENT_META = {
  order_status: { label: "Order status", chip: "bg-violet-50 text-violet-700 ring-violet-600/20", emoji: "📦" },
  order_query: { label: "Order query", chip: "bg-fuchsia-50 text-fuchsia-700 ring-fuchsia-600/20", emoji: "🧾" },
  faq: { label: "FAQ", chip: "bg-sky-50 text-sky-700 ring-sky-600/20", emoji: "💡" },
  support: { label: "Support", chip: "bg-amber-50 text-amber-700 ring-amber-600/20", emoji: "🤝" },
  greeting: { label: "Greeting", chip: "bg-brand-50 text-brand-700 ring-brand-600/20", emoji: "👋" },
  unknown: { label: "Unknown", chip: "bg-slate-100 text-slate-600 ring-slate-500/20", emoji: "❓" },
};

export const EVENT_META = {
  order_cancelled: { label: "Cancelled", emoji: "❌", chip: "bg-rose-50 text-rose-700 ring-rose-600/20", dot: "bg-rose-500" },
  return_requested: { label: "Return", emoji: "↩️", chip: "bg-orange-50 text-orange-700 ring-orange-600/20", dot: "bg-orange-500" },
  replacement_requested: { label: "Replacement", emoji: "🔁", chip: "bg-violet-50 text-violet-700 ring-violet-600/20", dot: "bg-violet-500" },
  refund_initiated: { label: "Refund", emoji: "💸", chip: "bg-brand-50 text-brand-700 ring-brand-600/20", dot: "bg-brand-500" },
  refund_completed: { label: "Refunded", emoji: "✅", chip: "bg-brand-50 text-brand-700 ring-brand-600/20", dot: "bg-brand-500" },
  human_callback: { label: "Callback", emoji: "📞", chip: "bg-amber-50 text-amber-700 ring-amber-600/20", dot: "bg-amber-500" },
  status_update: { label: "Auto-update", emoji: "🚚", chip: "bg-sky-50 text-sky-700 ring-sky-600/20", dot: "bg-sky-500" },
  goodwill_coupon: { label: "Goodwill", emoji: "🎁", chip: "bg-pink-50 text-pink-700 ring-pink-600/20", dot: "bg-pink-500" },
};

const INR = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
export function money(value, currency = "INR") {
  if (currency === "INR") return INR.format(value || 0);
  return `${currency} ${Math.round(value || 0)}`;
}

export function initials(name = "") {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
}

// Deterministic gradient avatar colour from a string (phone/name).
const AVATAR_COLORS = [
  "from-rose-400 to-rose-600", "from-orange-400 to-orange-600",
  "from-amber-400 to-amber-600", "from-lime-400 to-lime-600",
  "from-emerald-400 to-emerald-600", "from-teal-400 to-teal-600",
  "from-cyan-400 to-cyan-600", "from-sky-400 to-sky-600",
  "from-indigo-400 to-indigo-600", "from-violet-400 to-violet-600",
  "from-fuchsia-400 to-fuchsia-600", "from-pink-400 to-pink-600",
];
export function avatarColor(key = "") {
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

export function timeAgo(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  const secs = Math.max(1, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function clockTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// WhatsApp-style *bold* / _italic_ → HTML (input is escaped first).
export function renderWhatsApp(text = "") {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped
    .replace(/\*(.+?)\*/g, "<strong>$1</strong>")
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/\n/g, "<br/>");
}
