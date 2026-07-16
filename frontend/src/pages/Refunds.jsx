import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Wallet, CheckCircle2, ShieldCheck, Clock } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Card, Chip, Spinner, EmptyState, Button, Avatar } from "../components/Primitives.jsx";
import { api } from "../api.js";
import { money, timeAgo, avatarColor, initials, classNames } from "../lib/ui.js";

export default function Refunds() {
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState("");
  const [done, setDone] = useState(0);

  async function load() {
    setRows(await api.pendingRefunds());
  }
  useEffect(() => {
    load();
  }, []);

  async function process(orderNumber) {
    setBusy(orderNumber);
    try {
      await api.completeRefund(orderNumber);
      setRows((r) => r.filter((x) => x.order_number !== orderNumber));
      setDone((d) => d + 1);
    } finally {
      setBusy("");
    }
  }

  const total = rows?.reduce((s, r) => s + (r.amount || 0), 0) || 0;

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Refunds"
        subtitle="The AI initiates refunds automatically — a human reviews and pays them out here."
      >
        {rows && (
          <div className="flex items-center gap-2">
            <Chip className="bg-amber-50 text-amber-700 ring-amber-600/20">
              <Clock className="h-3 w-3" /> {rows.length} pending
            </Chip>
            {done > 0 && (
              <Chip className="bg-brand-50 text-brand-700 ring-brand-600/20">
                <CheckCircle2 className="h-3 w-3" /> {done} paid today
              </Chip>
            )}
          </div>
        )}
      </PageHeader>

      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        {!rows && (
          <div className="flex justify-center py-16">
            <Spinner className="h-8 w-8" />
          </div>
        )}

        {rows && rows.length === 0 && (
          <EmptyState icon={ShieldCheck} title="All caught up! 🎉" subtitle="No refunds are waiting to be paid out." />
        )}

        {rows && rows.length > 0 && (
          <>
            <Card className="mb-5 flex items-center justify-between p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                  <Wallet className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-sm text-slate-500">Total awaiting payout</p>
                  <p className="text-2xl font-extrabold text-slate-900">{money(total)}</p>
                </div>
              </div>
              <p className="max-w-xs text-right text-xs text-slate-400">
                Review each refund and click <span className="font-semibold text-slate-600">Pay refund</span> to
                complete it. The customer is notified on WhatsApp.
              </p>
            </Card>

            <div className="space-y-3">
              <AnimatePresence initial={false}>
                {rows.map((r) => (
                  <motion.div
                    key={r.order_number}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, x: 40, transition: { duration: 0.25 } }}
                  >
                    <Card className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
                      <Avatar name={initials(r.customer_name || "?")} colorClass={avatarColor(r.contact_number || r.order_number)} />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-sm font-bold text-slate-900">{r.order_number}</span>
                          <Chip className={classNames(
                            r.refund_status === "processing"
                              ? "bg-sky-50 text-sky-700 ring-sky-600/20"
                              : "bg-amber-50 text-amber-700 ring-amber-600/20"
                          )}>
                            {r.refund_status}
                          </Chip>
                          <span className="text-xs text-slate-400">{timeAgo(r.requested_on)}</span>
                        </div>
                        <p className="mt-0.5 truncate text-sm text-slate-600">
                          {r.customer_name}
                          {r.reason && <span className="text-slate-400"> · {r.reason}</span>}
                        </p>
                        <p className="mt-0.5 text-xs text-slate-400">
                          {r.method} · Ref {r.reference} · order {String(r.order_status).replace("OrderStatus.", "").replace("_", " ")}
                        </p>
                      </div>
                      <div className="flex items-center gap-4 sm:flex-col sm:items-end">
                        <span className="text-lg font-extrabold text-slate-900">{money(r.amount)}</span>
                        <Button onClick={() => process(r.order_number)} disabled={busy === r.order_number}>
                          {busy === r.order_number ? <Spinner className="h-4 w-4 text-white" /> : <CheckCircle2 className="h-4 w-4" />}
                          Pay refund
                        </Button>
                      </div>
                    </Card>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
