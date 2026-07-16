import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Inbox as InboxIcon, Send, CheckCircle2, Bot, User, Headset } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Avatar, Chip, Spinner, EmptyState, Button } from "../components/Primitives.jsx";
import { api } from "../api.js";
import {
  CONVO_STATUS,
  INTENT_META,
  avatarColor,
  initials,
  renderWhatsApp,
  clockTime,
  timeAgo,
  classNames,
} from "../lib/ui.js";

const FILTERS = [
  { key: "", label: "All" },
  { key: "needs_human", label: "Needs human" },
  { key: "open", label: "AI handling" },
  { key: "resolved", label: "Resolved" },
];

export default function InboxPage() {
  const [filter, setFilter] = useState("");
  const [list, setList] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadList() {
    const data = await api.conversations(filter);
    setList(data);
    if (!activeId && data.length) setActiveId(data[0].id);
  }

  useEffect(() => {
    loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  useEffect(() => {
    if (!activeId) return;
    api.conversation(activeId).then(setDetail);
  }, [activeId]);

  async function sendReply() {
    if (!reply.trim() || busy) return;
    setBusy(true);
    try {
      await api.agentReply(activeId, reply.trim());
      setReply("");
      setDetail(await api.conversation(activeId));
      loadList();
    } finally {
      setBusy(false);
    }
  }

  async function resolve() {
    setBusy(true);
    try {
      await api.setConversationStatus(activeId, "resolved");
      setDetail(await api.conversation(activeId));
      loadList();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Inbox" subtitle="Conversations your AI has handled — jump in whenever a human is needed." />
      <div className="flex min-h-0 flex-1">
        {/* Conversation list */}
        <div className="flex w-full max-w-sm flex-col border-r border-slate-200 bg-white/60 backdrop-blur">
          <div className="scroll-fade-x flex gap-1.5 overflow-x-auto p-3">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={classNames(
                  "shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold transition",
                  filter === f.key ? "bg-slate-900 text-white shadow-sm" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            {!list && (
              <div className="flex justify-center py-10">
                <Spinner />
              </div>
            )}
            {list && list.length === 0 && <EmptyState icon={InboxIcon} title="No conversations" subtitle="Try the Live Chat to create one." />}
            {list?.map((c, idx) => {
              const s = CONVO_STATUS[c.status] || CONVO_STATUS.open;
              const active = activeId === c.id;
              return (
                <motion.button
                  key={c.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.03 }}
                  whileHover={{ x: 3 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={() => setActiveId(c.id)}
                  className={classNames(
                    "relative flex w-full items-start gap-3 border-b border-slate-100 px-4 py-3 text-left transition-colors duration-200",
                    active ? "bg-brand-50/70" : "hover:bg-slate-50"
                  )}
                >
                  {active && <span className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-brand-500" />}
                  <Avatar name={initials(c.customer.name)} colorClass={avatarColor(c.customer.wa_id)} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate font-semibold text-slate-800">{c.customer.name}</p>
                      <span className="shrink-0 text-[11px] text-slate-400">{timeAgo(c.last_message_at)}</span>
                    </div>
                    <p className="truncate text-sm text-slate-500">{c.last_message_preview || "—"}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <Chip className={s.chip}>
                        <span className={classNames("h-1.5 w-1.5 rounded-full", s.dot)} />
                        {s.label}
                      </Chip>
                      {c.priority && (
                        <Chip className="bg-rose-50 text-rose-700 ring-rose-600/20">🔥 Priority</Chip>
                      )}
                    </div>
                  </div>
                </motion.button>
              );
            })}
          </div>
        </div>

        {/* Thread */}
        <div className="flex min-w-0 flex-1 flex-col bg-slate-50/60">
          {!detail ? (
            <div className="flex h-full items-center justify-center">
              <EmptyState icon={InboxIcon} title="Select a conversation" subtitle="Pick one from the list to view the thread." />
            </div>
          ) : (
            <>
              {/* Thread header */}
              <div className="flex items-center gap-3 border-b border-slate-200 bg-white/80 px-5 py-3 backdrop-blur">
                <Avatar name={initials(detail.customer.name)} colorClass={avatarColor(detail.customer.wa_id)} ring />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-slate-800">{detail.customer.name}</p>
                  <p className="truncate text-xs text-slate-500">+{detail.customer.wa_id}</p>
                </div>
                {detail.status !== "resolved" && (
                  <Button variant="ghost" onClick={resolve} disabled={busy}>
                    <CheckCircle2 className="h-4 w-4" /> Resolve
                  </Button>
                )}
                <Chip className={(CONVO_STATUS[detail.status] || CONVO_STATUS.open).chip}>
                  {(CONVO_STATUS[detail.status] || CONVO_STATUS.open).label}
                </Chip>
              </div>

              {/* Messages */}
              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-4">
                <AnimatePresence initial={false}>
                  {detail.messages.map((m) => {
                    const inbound = m.direction === "inbound";
                    return (
                      <motion.div
                        key={m.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={classNames("flex", inbound ? "justify-start" : "justify-end")}
                      >
                        <div className="max-w-[70%]">
                          <div
                            className={classNames(
                              "rounded-2xl px-4 py-2.5 text-sm shadow-sm",
                              inbound
                                ? "rounded-tl-sm bg-white text-slate-800 ring-1 ring-slate-100"
                                : m.sender === "agent"
                                ? "rounded-tr-sm bg-slate-800 text-white"
                                : "rounded-tr-sm bg-gradient-to-br from-brand-500 to-brand-600 text-white"
                            )}
                          >
                            <p className="whitespace-pre-wrap break-words leading-relaxed" dangerouslySetInnerHTML={{ __html: renderWhatsApp(m.content) }} />
                          </div>
                          <div className={classNames("mt-1 flex items-center gap-2 text-[11px] text-slate-400", inbound ? "justify-start" : "justify-end")}>
                            <span className="flex items-center gap-1">
                              {inbound ? <User className="h-3 w-3" /> : m.sender === "agent" ? <Headset className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                              {inbound ? "Customer" : m.sender === "agent" ? "You" : "AI"}
                            </span>
                            {inbound && m.intent && (
                              <span>{(INTENT_META[m.intent] || INTENT_META.unknown).emoji} {(INTENT_META[m.intent] || INTENT_META.unknown).label}</span>
                            )}
                            <span>{clockTime(m.created_at)}</span>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>

              {/* Agent composer */}
              <div className="flex items-center gap-2 border-t border-slate-200 bg-white/80 px-4 py-3 backdrop-blur">
                <input
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendReply()}
                  placeholder="Reply as a human agent…"
                  className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
                />
                <Button onClick={sendReply} disabled={busy || !reply.trim()}>
                  <Send className="h-4 w-4" /> Send
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
