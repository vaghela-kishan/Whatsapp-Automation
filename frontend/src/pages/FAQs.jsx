import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, Plus, Trash2, Check, X, Tag, Sparkles } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Card, Chip, Skeleton, Button, EmptyState, stagger, rise } from "../components/Primitives.jsx";
import { api } from "../api.js";

const CATEGORY_CHIP = {
  Shipping: "bg-violet-50 text-violet-700 ring-violet-600/20",
  Returns: "bg-orange-50 text-orange-700 ring-orange-600/20",
  Payments: "bg-sky-50 text-sky-700 ring-sky-600/20",
  Warranty: "bg-amber-50 text-amber-700 ring-amber-600/20",
  General: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

const EMPTY = { question: "", answer: "", category: "General", keywords: "" };

export default function FAQs() {
  const [faqs, setFaqs] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [answers, setAnswers] = useState({}); // suggestionId -> draft answer
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  async function load() {
    setFaqs(await api.faqs());
    api.faqSuggestions().then(setSuggestions).catch(() => setSuggestions([]));
  }
  useEffect(() => {
    load();
  }, []);

  async function approveSuggestion(s) {
    const answer = (answers[s.id] || "").trim();
    if (!answer) return;
    setBusy(true);
    try {
      await api.approveSuggestion(s.id, { answer, category: "General" });
      setSuggestions((list) => list.filter((x) => x.id !== s.id));
      load();
    } finally {
      setBusy(false);
    }
  }

  async function dismissSuggestion(s) {
    await api.dismissSuggestion(s.id);
    setSuggestions((list) => list.filter((x) => x.id !== s.id));
  }

  async function create() {
    if (!draft.question.trim() || !draft.answer.trim()) return;
    setBusy(true);
    try {
      await api.createFaq(draft);
      setDraft(EMPTY);
      setCreating(false);
      load();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id) {
    await api.deleteFaq(id);
    load();
  }

  const grouped = (faqs || []).reduce((acc, f) => {
    (acc[f.category] ||= []).push(f);
    return acc;
  }, {});

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Knowledge Base" subtitle="Answers the AI quotes automatically. Add one and it's live instantly.">
        <Button onClick={() => setCreating((v) => !v)}>
          <Plus className={`h-4 w-4 transition-transform ${creating ? "rotate-45" : ""}`} /> Add FAQ
        </Button>
      </PageHeader>

      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        <AnimatePresence>
          {creating && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="mb-6 rounded-2xl bg-white/85 p-5 shadow-card ring-1 ring-slate-200/70 backdrop-blur-sm">
                <div className="grid gap-3 sm:grid-cols-2">
                  <input
                    value={draft.question}
                    onChange={(e) => setDraft({ ...draft, question: e.target.value })}
                    placeholder="Question"
                    className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 sm:col-span-2"
                  />
                  <textarea
                    value={draft.answer}
                    onChange={(e) => setDraft({ ...draft, answer: e.target.value })}
                    placeholder="Answer (supports *bold*)"
                    rows={3}
                    className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 sm:col-span-2"
                  />
                  <select
                    value={draft.category}
                    onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                    className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400"
                  >
                    {["General", "Shipping", "Returns", "Payments", "Warranty"].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                  <input
                    value={draft.keywords}
                    onChange={(e) => setDraft({ ...draft, keywords: e.target.value })}
                    placeholder="Match keywords (comma or space separated)"
                    className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
                  />
                </div>
                <div className="mt-3 flex justify-end gap-2">
                  <Button variant="subtle" onClick={() => { setCreating(false); setDraft(EMPTY); }}>
                    <X className="h-4 w-4" /> Cancel
                  </Button>
                  <Button onClick={create} disabled={busy}>
                    <Check className="h-4 w-4" /> Save FAQ
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Self-learning: questions the bot couldn't answer, awaiting an answer */}
        {suggestions.length > 0 && (
          <Card className="mb-6 border border-amber-200/70 bg-amber-50/40 p-5">
            <div className="mb-3 flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
                <Sparkles className="h-4 w-4" />
              </span>
              <div>
                <h2 className="font-bold text-slate-900">Learn from customers</h2>
                <p className="text-xs text-slate-500">
                  Questions the AI couldn't answer. Add an answer to teach it — it goes live instantly.
                </p>
              </div>
            </div>
            <div className="space-y-3">
              {suggestions.map((s) => (
                <div key={s.id} className="rounded-xl bg-white p-3 ring-1 ring-slate-200">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-slate-800">{s.question}</p>
                    <Chip className="bg-amber-100 text-amber-700 ring-amber-600/20">asked ×{s.ask_count}</Chip>
                  </div>
                  <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                    <input
                      value={answers[s.id] || ""}
                      onChange={(e) => setAnswers((a) => ({ ...a, [s.id]: e.target.value }))}
                      placeholder="Write the answer to teach the bot…"
                      className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
                    />
                    <div className="flex gap-2">
                      <Button onClick={() => approveSuggestion(s)} disabled={busy || !(answers[s.id] || "").trim()}>
                        <Check className="h-4 w-4" /> Publish
                      </Button>
                      <Button variant="subtle" onClick={() => dismissSuggestion(s)}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {!faqs && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-40" />
            ))}
          </div>
        )}
        {faqs && faqs.length === 0 && !creating && (
          <EmptyState icon={BookOpen} title="No FAQs yet" subtitle="Add your first knowledge-base answer." />
        )}

        <div className="space-y-8">
          {Object.entries(grouped).map(([category, items]) => (
            <div key={category}>
              <div className="mb-3 flex items-center gap-2">
                <Chip className={CATEGORY_CHIP[category] || CATEGORY_CHIP.General}>{category}</Chip>
                <span className="text-xs text-slate-400">{items.length} answers</span>
              </div>
              <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {items.map((f) => (
                  <motion.div
                    key={f.id}
                    variants={rise}
                    whileHover={{ y: -4, transition: { type: "spring", stiffness: 400, damping: 22 } }}
                    className="group cursor-default rounded-2xl bg-white/85 p-5 shadow-card ring-1 ring-slate-200/70 backdrop-blur-sm transition-shadow duration-200 hover:shadow-soft hover:ring-brand-300/60"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="font-semibold text-slate-800">{f.question}</p>
                      <button
                        onClick={() => remove(f.id)}
                        className="rounded-lg p-1.5 text-slate-300 opacity-0 transition hover:bg-rose-50 hover:text-rose-500 group-hover:opacity-100"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-500">{f.answer}</p>
                    <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
                      {f.keywords ? (
                        <span className="flex items-center gap-1 truncate text-xs text-slate-400">
                          <Tag className="h-3 w-3" /> {f.keywords}
                        </span>
                      ) : (
                        <span />
                      )}
                      <Chip className="bg-slate-100 text-slate-600 ring-slate-500/20">{f.hit_count} hits</Chip>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
