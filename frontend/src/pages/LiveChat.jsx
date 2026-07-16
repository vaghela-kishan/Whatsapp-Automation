import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Bot,
  Phone,
  Video,
  MoreVertical,
  Check,
  CheckCheck,
  RefreshCw,
  Sparkles,
  ShieldAlert,
  Smile,
  Paperclip,
  User,
} from "lucide-react";
import { api } from "../api.js";
import { INTENT_META, renderWhatsApp, clockTime, classNames } from "../lib/ui.js";
import { Chip } from "../components/Primitives.jsx";

const SUGGESTIONS = [
  "Where are my orders?",
  "Track my latest order",
  "Cancel an order",
  "I want to return an item",
  "My refund status",
  "Download my invoice",
  "mara order details batavo",
];

function newWaId() {
  let n = "9198";
  for (let i = 0; i < 8; i++) n += Math.floor(Math.random() * 10);
  return n;
}

export default function LiveChat({ info }) {
  const [identities, setIdentities] = useState([]);
  const [identity, setIdentity] = useState(null); // selected demo customer or null = new number
  const [waId, setWaId] = useState(newWaId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [lastMeta, setLastMeta] = useState(null);
  const scrollRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  // Load demo customers (who own orders) and default to the first, so
  // "where are my orders?" works out of the box.
  useEffect(() => {
    api.demoIdentities().then((list) => {
      setIdentities(list || []);
      if (list && list.length) {
        setIdentity(list[0]);
        setWaId(list[0].wa_id);
      }
    }).catch(() => setIdentities([]));
  }, []);

  function pickIdentity(value) {
    if (value === "__new__") {
      setIdentity(null);
      setWaId(newWaId());
    } else {
      const found = identities.find((i) => i.wa_id === value);
      setIdentity(found || null);
      setWaId(found ? found.wa_id : newWaId());
    }
    setMessages([]);
    setLastMeta(null);
  }

  async function send(text) {
    const clean = text.trim();
    if (!clean || sending) return;
    setInput("");
    const now = new Date().toISOString();
    setMessages((m) => [...m, { id: `local-${Date.now()}`, sender: "customer", content: clean, created_at: now }]);
    setSending(true);
    try {
      const res = await api.sendMessage({ wa_id: waId, name: identity?.name || "You", text: clean });
      setMessages((m) => [
        ...m,
        {
          id: res.reply.id,
          sender: "ai",
          content: res.reply.content,
          created_at: res.reply.created_at,
          intent: res.intent,
          confidence: res.reply.confidence,
          escalated: res.escalated,
        },
      ]);
      setLastMeta({ intent: res.intent, confidence: res.reply.confidence, escalated: res.escalated });
    } catch (e) {
      setMessages((m) => [
        ...m,
        { id: `err-${Date.now()}`, sender: "ai", content: `⚠️ ${e.message}`, created_at: new Date().toISOString() },
      ]);
    } finally {
      setSending(false);
    }
  }

  function reset() {
    // Clear the thread but keep the selected identity.
    if (!identity) setWaId(newWaId());
    setMessages([]);
    setLastMeta(null);
  }

  async function onPickFile(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || sending) return;
    const dataUrl = await new Promise((res) => {
      const r = new FileReader();
      r.onload = () => res(r.result);
      r.readAsDataURL(file);
    });
    const now = new Date().toISOString();
    setMessages((m) => [
      ...m,
      { id: `img-${Date.now()}`, sender: "customer", content: "", image: dataUrl, created_at: now },
    ]);
    setSending(true);
    try {
      const res = await api.sendPhoto({
        wa_id: waId,
        name: identity?.name || "You",
        text: input.trim(),
        image_base64: dataUrl,
        mime_type: file.type || "image/jpeg",
      });
      setInput("");
      setMessages((m) => [
        ...m,
        {
          id: res.reply.id,
          sender: "ai",
          content: res.reply.content,
          created_at: res.reply.created_at,
          intent: res.intent,
          confidence: res.reply.confidence,
          escalated: res.escalated,
        },
      ]);
      setLastMeta({ intent: res.intent, confidence: res.reply.confidence, escalated: res.escalated });
    } catch (err) {
      setMessages((m) => [
        ...m,
        { id: `err-${Date.now()}`, sender: "ai", content: `⚠️ ${err.message}`, created_at: new Date().toISOString() },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full">
      {/* Chat column */}
      <div className="flex min-w-0 flex-1 flex-col bg-slate-200">
        {/* WhatsApp header */}
        <div className="flex items-center gap-3 bg-gradient-to-r from-[#075e54] to-[#008069] px-4 py-2.5 text-white shadow-md">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-full bg-white/15 ring-1 ring-white/20">
            <Bot className="h-6 w-6" />
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-brand-400 ring-2 ring-[#008069]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-semibold leading-tight">
              {info?.assistant_name || "Ava"} · {info?.business_name || "Aurora Store"}
            </p>
            <p className="truncate text-xs text-white/80">
              {sending ? (
                <span className="inline-flex items-center gap-1">
                  <span className="typing-dot h-1 w-1 rounded-full bg-white/90" />
                  <span className="typing-dot h-1 w-1 rounded-full bg-white/90" />
                  <span className="typing-dot h-1 w-1 rounded-full bg-white/90" />
                  <span className="ml-1">typing…</span>
                </span>
              ) : (
                "online · AI assistant"
              )}
            </p>
          </div>
          <Phone className="h-5 w-5 opacity-90" />
          <Video className="h-5 w-5 opacity-90" />
          <button onClick={reset} title="New conversation" className="rounded-full p-1.5 transition hover:bg-white/10">
            <RefreshCw className="h-5 w-5 opacity-90" />
          </button>
          <MoreVertical className="h-5 w-5 opacity-90" />
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="chat-wallpaper flex-1 space-y-2 overflow-y-auto px-4 py-4 sm:px-16">
          <div className="mx-auto mb-2 w-fit rounded-lg bg-[#ffeecd] px-3 py-1 text-center text-xs text-slate-600 shadow-sm">
            🔒 Messages are automated end-to-end by AI. Try a suggestion below.
          </div>

          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mx-auto mt-8 max-w-sm rounded-2xl bg-white/85 p-6 text-center shadow-soft ring-1 ring-white/60"
            >
              <div className="mx-auto mb-3 flex h-14 w-14 animate-float items-center justify-center rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 text-white shadow-glow">
                <Sparkles className="h-7 w-7" />
              </div>
              <p className="font-bold text-slate-800">Chat with {info?.assistant_name || "Ava"}</p>
              <p className="mt-1 text-sm text-slate-500">
                Ask about an order, delivery, returns or payments — the AI replies instantly.
              </p>
            </motion.div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((m) => {
              const mine = m.sender === "customer";
              return (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: "spring", stiffness: 320, damping: 26 }}
                  className={classNames("flex", mine ? "justify-end" : "justify-start")}
                >
                  <div
                    className={classNames(
                      "relative max-w-[80%] rounded-lg px-3 py-2 text-sm shadow-sm sm:max-w-[65%]",
                      mine ? "bubble-out rounded-tr-none bg-[#d9fdd3] text-slate-800" : "bubble-in rounded-tl-none bg-white text-slate-800"
                    )}
                  >
                    {!mine && m.intent && (
                      <div className="mb-1 flex items-center gap-1.5">
                        <span className="text-[11px] font-semibold text-brand-600">
                          {(INTENT_META[m.intent] || INTENT_META.unknown).emoji}{" "}
                          {(INTENT_META[m.intent] || INTENT_META.unknown).label}
                        </span>
                      </div>
                    )}
                    {m.image && (
                      <img
                        src={m.image}
                        alt="uploaded"
                        className="mb-1 max-h-52 w-full rounded-lg object-cover"
                      />
                    )}
                    {m.content && (
                      <p
                        className="whitespace-pre-wrap break-words leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: renderWhatsApp(m.content) }}
                      />
                    )}
                    <div className="mt-0.5 flex items-center justify-end gap-1">
                      <span className="text-[10px] text-slate-400">{clockTime(m.created_at)}</span>
                      {mine && <CheckCheck className="h-3.5 w-3.5 text-sky-500" />}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {sending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
              <div className="bubble-in relative flex items-center gap-1 rounded-lg rounded-tl-none bg-white px-4 py-3 shadow-sm">
                <span className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
                <span className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
                <span className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
              </div>
            </motion.div>
          )}
        </div>

        {/* Suggestions */}
        <div className="scroll-fade-x flex gap-2 overflow-x-auto bg-slate-100 px-3 py-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              disabled={sending}
              className="shrink-0 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:-translate-y-0.5 hover:border-brand-400 hover:text-brand-700 hover:shadow-sm disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>

        {/* Composer */}
        <div className="flex items-center gap-2 bg-slate-100 px-3 pb-3">
          <div className="flex flex-1 items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 shadow-sm focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100">
            <Smile className="h-5 w-5 shrink-0 text-slate-400" />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              placeholder="Type a message, or 📎 send a photo"
              className="min-w-0 flex-1 bg-transparent py-1 text-sm outline-none"
            />
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onPickFile} />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={sending}
              title="Send a product photo"
              className="shrink-0 text-slate-400 transition hover:text-brand-600 disabled:opacity-50"
            >
              <Paperclip className="h-5 w-5" />
            </button>
          </div>
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={() => send(input)}
            disabled={sending || !input.trim()}
            className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-[#00a884] to-[#008069] text-white shadow-md transition hover:shadow-lg disabled:opacity-50"
          >
            <Send className="h-5 w-5" />
          </motion.button>
        </div>
      </div>

      {/* AI insight side panel */}
      <div className="hidden w-72 shrink-0 flex-col gap-4 border-l border-slate-200 bg-white/70 p-5 backdrop-blur-xl xl:flex">
        <div>
          <h3 className="flex items-center gap-2 font-bold text-slate-900">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 text-white">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            AI Insight
          </h3>
          <p className="mt-1 text-xs text-slate-500">Live view of how the assistant handled the last message.</p>
        </div>

        <AnimatePresence mode="wait">
          {lastMeta ? (
            <motion.div
              key={JSON.stringify(lastMeta)}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              <div className="rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-100">
                <p className="text-xs font-medium text-slate-500">Detected intent</p>
                <div className="mt-1.5">
                  <Chip className={(INTENT_META[lastMeta.intent] || INTENT_META.unknown).chip}>
                    {(INTENT_META[lastMeta.intent] || INTENT_META.unknown).emoji}{" "}
                    {(INTENT_META[lastMeta.intent] || INTENT_META.unknown).label}
                  </Chip>
                </div>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-100">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-slate-500">Confidence</p>
                  <p className="text-sm font-bold text-slate-800">{Math.round((lastMeta.confidence || 0) * 100)}%</p>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.round((lastMeta.confidence || 0) * 100)}%` }}
                    transition={{ duration: 0.7, ease: "easeOut" }}
                    className={classNames(
                      "h-full rounded-full",
                      lastMeta.confidence > 0.75 ? "bg-brand-500" : lastMeta.confidence > 0.5 ? "bg-amber-500" : "bg-rose-500"
                    )}
                  />
                </div>
              </div>

              <div
                className={classNames(
                  "flex items-start gap-2 rounded-2xl p-4 text-sm ring-1",
                  lastMeta.escalated ? "bg-amber-50 text-amber-800 ring-amber-100" : "bg-brand-50 text-brand-800 ring-brand-100"
                )}
              >
                {lastMeta.escalated ? (
                  <>
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>Escalated to a human agent — it now appears in the Inbox.</span>
                  </>
                ) : (
                  <>
                    <Check className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>Resolved automatically by AI — no human needed.</span>
                  </>
                )}
              </div>
            </motion.div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-center text-sm text-slate-400">
              Send a message to see the AI's reasoning here.
            </div>
          )}
        </AnimatePresence>

        <div className="mt-auto space-y-2">
          <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
            <User className="h-3.5 w-3.5" /> Chatting as
          </label>
          <select
            value={identity ? identity.wa_id : "__new__"}
            onChange={(e) => pickIdentity(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
          >
            {identities.map((i) => (
              <option key={i.wa_id} value={i.wa_id}>
                {i.name} · {i.order_count} orders
              </option>
            ))}
            <option value="__new__">New number (no orders)</option>
          </select>
          <div className="overflow-hidden rounded-2xl bg-slate-900 p-3 text-xs text-slate-300">
            <p className="font-mono text-[11px] text-slate-400">
              {identity ? "customer" : "new session"}
            </p>
            <p className="mt-0.5 font-mono text-brand-300">+{waId}</p>
            <p className="mt-1 text-[11px] text-slate-400">
              {identity
                ? `Try: "where are my orders?"`
                : "No orders linked — pick a customer above to demo."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
