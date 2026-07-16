import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Package, Search, Truck, Loader2 } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Chip, Skeleton, EmptyState, Button, stagger, rise } from "../components/Primitives.jsx";
import { api } from "../api.js";
import { ORDER_STATUS, money, classNames } from "../lib/ui.js";

const PAGE = 48;

const STATUS_FILTERS = [
  { key: "", label: "All" },
  { key: "delivered", label: "Delivered" },
  { key: "shipped", label: "Shipped" },
  { key: "out_for_delivery", label: "Out for delivery" },
  { key: "packed", label: "Packed" },
  { key: "confirmed", label: "Confirmed" },
  { key: "pending", label: "Pending" },
  { key: "cancelled", label: "Cancelled" },
  { key: "returned", label: "Returned" },
];

export default function Orders() {
  const [orders, setOrders] = useState(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [visible, setVisible] = useState(PAGE);

  useEffect(() => {
    api.orders().then(setOrders);
  }, []);

  const filtered = useMemo(() => {
    if (!orders) return [];
    const q = query.trim().toLowerCase();
    return orders.filter((o) => {
      if (status && o.status !== status) return false;
      if (!q) return true;
      return (
        o.order_number.toLowerCase().includes(q) ||
        o.items.some((it) => (it.name || "").toLowerCase().includes(q))
      );
    });
  }, [orders, query, status]);

  useEffect(() => setVisible(PAGE), [query, status]);

  const shown = filtered.slice(0, visible);

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Orders" subtitle="Every order the assistant can look up over WhatsApp.">
        <div className="flex items-center gap-2">
          {orders && (
            <Chip className="bg-slate-100 text-slate-600 ring-slate-500/20">{orders.length.toLocaleString()} total</Chip>
          )}
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search order # or item"
              className="w-56 rounded-xl border border-slate-200 bg-white/80 py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            />
          </div>
        </div>
      </PageHeader>

      {/* Status filter row */}
      {orders && (
        <div className="scroll-fade-x flex gap-1.5 overflow-x-auto border-b border-slate-200/70 bg-white/50 px-6 py-3 backdrop-blur">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setStatus(f.key)}
              className={classNames(
                "shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold transition",
                status === f.key ? "bg-slate-900 text-white shadow-sm" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        {!orders && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 9 }).map((_, i) => (
              <Skeleton key={i} className="h-48" />
            ))}
          </div>
        )}
        {orders && filtered.length === 0 && <EmptyState icon={Package} title="No orders found" subtitle="Try a different search or filter." />}

        {orders && filtered.length > 0 && (
          <>
            <p className="mb-4 text-sm text-slate-400">
              Showing <span className="font-semibold text-slate-600">{shown.length}</span> of{" "}
              <span className="font-semibold text-slate-600">{filtered.length.toLocaleString()}</span> orders
            </p>
            <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {shown.map((o) => {
                const s = ORDER_STATUS[o.status] || ORDER_STATUS.pending;
                return (
                  <motion.div
                    key={o.id}
                    variants={rise}
                    whileHover={{ y: -6, transition: { type: "spring", stiffness: 400, damping: 22 } }}
                    className="group relative cursor-pointer overflow-hidden rounded-2xl bg-white/85 p-5 shadow-card ring-1 ring-slate-200/70 backdrop-blur-sm transition-shadow duration-200 hover:shadow-soft hover:ring-brand-300/60"
                  >
                    <span className="absolute inset-x-0 top-0 h-1 scale-x-0 bg-gradient-to-r from-brand-400 to-brand-600 transition-transform duration-300 group-hover:scale-x-100" />
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-mono text-sm font-bold text-slate-900">{o.order_number}</p>
                        <p className="mt-0.5 text-xs text-slate-400">
                          {new Date(o.created_at).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" })}
                        </p>
                      </div>
                      <Chip className={s.chip}>{s.label}</Chip>
                    </div>

                    <div className="mt-4 space-y-1.5">
                      {o.items.map((it, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <span className="truncate text-slate-600">
                            {it.name} <span className="text-slate-400">×{it.qty}</span>
                          </span>
                          <span className="font-medium text-slate-700">{money(it.price, o.currency)}</span>
                        </div>
                      ))}
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
                      <span className="text-xs font-medium text-slate-400">Total</span>
                      <span className="text-lg font-extrabold text-slate-900">{money(o.total, o.currency)}</span>
                    </div>

                    {o.tracking_number && (
                      <div className="mt-3 flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500 ring-1 ring-slate-100">
                        <Truck className="h-4 w-4 text-brand-500" />
                        <span className="font-mono">{o.tracking_number}</span>
                        {o.carrier && <span className="text-slate-400">· {o.carrier}</span>}
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </motion.div>

            {visible < filtered.length && (
              <div className="mt-8 flex justify-center">
                <Button variant="ghost" onClick={() => setVisible((v) => v + PAGE)}>
                  <Loader2 className="h-4 w-4" /> Load more ({(filtered.length - visible).toLocaleString()} left)
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
