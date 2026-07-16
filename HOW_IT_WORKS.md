# 📖 How It Works — Complete Guide

> **What this project is:** an **AI-powered WhatsApp customer-support platform** for an
> e-commerce store. A customer messages on WhatsApp; an AI agent (Google Gemini)
> understands them in any language, looks things up in a database, performs real
> actions (track / cancel / return / refund / replace), verifies damage from photos,
> and only escalates to a human when needed. A web dashboard lets the shop's team
> watch everything and step in.
>
> This document explains **everything**: the architecture, how a message travels
> through the system, every data model, and every feature. You can paste it into
> ChatGPT and ask follow-up questions.

---

## 1. The big picture (30-second version)

```
                     ┌──────────────────────────────────────────────┐
   Customer          │                 BACKEND (FastAPI)            │
   on WhatsApp  ───►  │  Webhook → Intent → AI Agent → Database → Reply│  ───► Reply back
   (or Live Chat)    │            (Gemini)   (tools)  (SQLite)       │       on WhatsApp
                     └──────────────────────────────────────────────┘
                                        ▲
                                        │ same data
                                        ▼
                     ┌──────────────────────────────────────────────┐
   Shop's team  ───►  │              FRONTEND (React dashboard)       │
   (humans)          │  Dashboard · Live Chat · Inbox · Orders ·     │
                     │  Refunds · Knowledge Base                     │
                     └──────────────────────────────────────────────┘
```

- **Backend** = the brain + database (Python / FastAPI). Runs on `http://127.0.0.1:8000`.
- **Frontend** = the dashboard the team uses (React). Runs on `http://localhost:5173`.
- **AI** = Google Gemini (with a built-in "mock" fallback so it works with no key).
- **WhatsApp** = Meta Cloud API (with a built-in "mock" simulator = the Live Chat page).
- **Database** = SQLite file `backend/dev.db` (can be swapped to PostgreSQL with one setting).

---

## 2. Tech stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend API | **FastAPI** (Python) | Fast, typed, auto docs at `/docs` |
| Database | **SQLite** (→ PostgreSQL ready) | Zero-setup dev; one env var to switch |
| ORM (DB access) | **SQLAlchemy 2** | Clean, portable data models |
| AI | **Google Gemini** (`google-generativeai`) | Function calling + vision + multilingual |
| WhatsApp | **Meta Cloud API** (httpx) | Real WhatsApp; mock for demo |
| Frontend | **React + Vite + Tailwind** | Fast, modern UI |
| Charts/animation | **Recharts + Framer Motion** | Dashboard visuals |

---

## 3. The message journey (the most important part)

When a customer sends **"Where is my order AUR-10432?"**, here is the exact path:

```
1. MESSAGE ARRIVES
   WhatsApp → POST /api/v1/webhook/whatsapp        (real)
   OR  Live Chat page → POST /api/v1/chat/send      (demo simulator)
        │
        ▼
2. IDENTIFY THE CUSTOMER            [conversation_service.handle_inbound]
   Look up (or create) the Customer by their phone number (wa_id).
   Open or continue their Conversation. Save the inbound Message.
        │
        ▼
3. UNDERSTAND THE MESSAGE           [intent.py]
   • classify()        → intent: order_status / order_query / faq / support / greeting / unknown
   • detect_sentiment()→ neutral / negative / angry
   • extract_order_number(), looks_non_english(), is_order_related()
        │
        ▼
4. DECIDE HOW TO ANSWER             [conversation_service]
   ┌─ Greeting?  → canned friendly reply (0 AI calls, any language)
   ├─ Order-related? → hand to the AI AGENT (Gemini function calling)  ── see §5
   ├─ FAQ?       → match the knowledge base; no match → log it (self-learning) + escalate
   └─ Other      → free-form AI reply
        │
        ▼
5. THE AI AGENT DOES THE WORK       [order_agent.py]
   Gemini reads the message + the conversation history, decides which
   DATABASE TOOL to call (see §6), the tool runs a real query/action,
   Gemini turns the result into a natural reply IN THE CUSTOMER'S LANGUAGE.
        │
        ▼
6. SAVE + SEND
   Save the outbound Message. Update the Conversation (preview, status,
   priority). Send the reply back over WhatsApp (mock outbox in demo).
        │
        ▼
7. REPLY REACHES THE CUSTOMER  ✅   (and everything is visible in the dashboard)
```

**Key idea:** every fact (order status, refund, invoice) comes from the **database via a
tool** — the AI never makes up order details. If the AI/quota is unavailable, deterministic
fallbacks still answer.

---

## 4. The data — what's stored and where

Everything lives in the SQLite database (`backend/dev.db`). Seven tables:

### `customers`
Who is messaging. `wa_id` (WhatsApp phone number) is the identity.
| field | meaning |
|-------|---------|
| wa_id | phone number (the login/identity) |
| name, email, avatar_url | contact details |

### `conversations`
One chat thread with a customer.
| field | meaning |
|-------|---------|
| status | `open` (AI handling) / `needs_human` / `resolved` |
| sentiment | `neutral` / `negative` / `angry` |
| priority | true = angry → shown first in the Inbox |
| last_message_preview, last_message_at | for the inbox list |

### `messages`
Every single message (in and out).
| field | meaning |
|-------|---------|
| direction | `inbound` (customer) / `outbound` (us) |
| sender | `customer` / `ai` / `agent` (human) / `system` |
| content | the text |
| intent, confidence | what the AI detected / how sure it was |

### `orders`  (the heart — 1,000 seeded)
| group | fields |
|-------|--------|
| identity | order_number (e.g. `AUR-10432`), customer_id |
| status | pending → confirmed → packed → shipped → out_for_delivery → delivered / cancelled / returned |
| items | list of `{name, qty, price}` |
| money | subtotal, discount, tax (18% GST), shipping_charges, **total** |
| payment | payment_method (UPI/Card/COD…), payment_status |
| invoice | invoice_number |
| delivery | tracking_number, carrier, estimated_delivery, delivered_at, delivery_attempts |
| cancel | cancelled_at, cancellation_reason |
| refund | refund_status (none/initiated/processing/completed), refund_amount, refund_method, refund_reference, refund_date |
| return | return_id, return_status, return_reason, replacement_id, pickup_date, return_eligible |

### `order_events`  (audit trail)
Every action ever taken on an order — a permanent history.
`event_type` = `order_cancelled` / `return_requested` / `replacement_requested` /
`refund_initiated` / `refund_completed` / `human_callback` / `status_update` / `goodwill_coupon`.
Stores the reason, a summary, who did it (`ai` / `agent` / `automation`), and structured data.

### `faqs`  (knowledge base)
Curated question/answer pairs the AI can quote, with `keywords` for matching and a `hit_count`.

### `faq_suggestions`  (self-learning)
Questions the AI **couldn't** answer — captured, de-duplicated, counted. An admin later
writes an answer and publishes it as a new FAQ.

---

## 5. How the AI works

### Two engines, automatic fallback
- **Gemini** (real AI) — set `AI_PROVIDER=gemini` + `GEMINI_API_KEY`.
- **Mock** (no key) — deterministic rule-based replies so the app *always* works.
- If Gemini errors or its free quota runs out, the code **silently falls back** — it never crashes.

### Function calling (the agentic part)
For any order-related message, Gemini is given a set of **tools** (Python functions that
touch the database). Gemini decides which to call, the tool runs, and Gemini writes the
final reply. This is what makes it feel like a real agent.

### Multi-turn memory
The last several messages are passed to Gemini as history, so follow-ups work:
*"return my order"* → *"which one?"* → *"AUR-20518"* → *"refund"* → done.

### Multi-language
Gemini is told to reply in the **same language/script** the customer used (Gujarati,
Hindi, Hinglish, English, …). Verified facts are passed to it so numbers stay exact.

---

## 6. The AI's tools (what it can actually do)

All tools are **scoped to the caller** — the AI can only see/act on *your* orders, never
anyone else's.

| Tool | What it does |
|------|--------------|
| `get_my_orders` | list all orders under your phone number |
| `get_order_details` | full breakdown of one order (items, tax, payment, invoice) |
| `track_order` | courier, tracking number, ETA, delivery attempts |
| `cancel_order` | cancel (only if Pending/Confirmed/Packed) — asks **why** first, starts a refund |
| `create_return_request` | return within 7 days (asks reason + refund/replacement; for damage asks for a **photo**) |
| `get_refund_status` | amount, status, method, reference, expected date |
| `get_invoice` | invoice number + GST download link |
| `apply_goodwill_coupon` | issues an apology discount coupon for upset customers |
| `request_human_callback` | logs a "human will call you back" request (no fake live transfer) |
| `search_orders` / `order_statistics` | admin-style search & totals |

---

## 7. Every feature, explained

**7.1 Order tracking / details / invoice** — ask in any language; the agent looks it up and
replies with real data.

**7.2 Cancellation** — allowed only before dispatch (Pending/Confirmed/Packed). The AI asks
*why* (reason is stored), confirms, cancels, and **initiates** a refund. If already shipped,
it politely refuses and offers a return instead.

**7.3 Returns & replacements** — allowed only for Delivered orders within a **7-day window**.
The AI asks the reason and whether you want a **Refund or Replacement**. For *Damaged / Wrong*
items it asks you to **send a photo** first (see 7.6). Creates a Return ID + pickup date.

**7.4 Refunds are human-in-the-loop** — the AI only *initiates* a refund (status = "initiated").
A human then reviews and pays it out on the **Refunds page** → status "completed" → the
customer gets a WhatsApp confirmation. (The AI never says "connecting you now, wait" — there
is no live agent; it promises a callback.)

**7.5 Proactive automation** — a background worker advances in-progress orders on a timer
(packed → shipped → out for delivery → delivered) and **proactively messages the customer**
at each step (*"🚚 Your order has shipped!"*). Every step is logged. (In production this would
be triggered by real courier webhooks.)

**7.6 Photo damage verification (Vision AI)** — the customer sends a photo (📎 button).
**Gemini Vision** inspects the image; if it sees real damage on a returnable order, it
**auto-approves the return + refund**. If it can't see damage, it asks for a clearer photo.

**7.7 Sentiment & priority** — angry messages ("worst service!!!", "fraud") are detected,
the conversation is flagged **🔥 Priority** and routed to a human, and it jumps to the top
of the Inbox.

**7.8 Self-learning FAQ** — when the AI can't answer a question, it's logged as a
**suggestion** (de-duplicated, with an "asked ×N" count). An admin writes the answer on the
Knowledge Base page and publishes it → the bot is smarter next time.

**7.9 Human escalation** — for disputes, fraud, or explicit "talk to a human", the AI logs a
callback request and tells the customer the team will reach out — the conversation appears in
the Inbox `Needs human` queue.

---

## 8. The dashboard (what the team sees)

| Page | Purpose |
|------|---------|
| **Dashboard** | live stats, message-volume chart, auto-resolution %, intents, top FAQs, and a **Recent activity** audit feed (+ "Run automation" button) |
| **Live Chat** | a pixel-accurate WhatsApp simulator to test the AI (pick which customer you are, send text or a 📎 photo) + an "AI Insight" panel |
| **Inbox** | every conversation; angry ones flagged Priority; a human can reply or resolve |
| **Orders** | all 1,000 orders with search + status filters |
| **Refunds** | the human queue — review AI-initiated refunds and "Pay refund" |
| **Knowledge Base** | manage FAQs + the "Learn from customers" self-learning suggestions |

---

## 9. Data flow — "from where to where"

```
CUSTOMER MESSAGE
   → webhook/chat endpoint
      → conversation_service.handle_inbound
         → intent.py (classify + sentiment)
         → order_agent (Gemini) ──calls──► tools ──read/write──► DATABASE
                                                                   │
         → reply text ◄──────────────────────────────────────────┘
      → save messages + update conversation  ──────────────────► DATABASE
   → WhatsApp provider (send reply)  ───────────────────────────► CUSTOMER

MEANWHILE, everything in the DATABASE is read by the FRONTEND:
   Dashboard/Inbox/Orders/Refunds/KB  ──GET──►  API  ──►  DATABASE
   Human actions (reply, resolve, pay refund, publish FAQ)  ──POST──►  API  ──►  DATABASE
   Proactive worker (timer)  ──►  advances orders + notifies  ──►  DATABASE + WhatsApp
```

---

## 10. Folder map

```
ai-support-platform/
├─ backend/                        FastAPI app
│  └─ app/
│     ├─ main.py                   app startup (+ starts the automation worker)
│     ├─ core/                     config, logging, errors, middleware
│     ├─ db/                       database engine, base, init + seeding
│     ├─ models/                   the 7 tables (Customer, Conversation, Message,
│     │                            Order, OrderEvent, FAQ, FAQSuggestion)
│     ├─ schemas/                  request/response shapes (Pydantic)
│     ├─ crud/                     database queries
│     ├─ services/                 the brains:
│     │   ├─ conversation_service.py   orchestrates every message
│     │   ├─ intent.py                 classify + sentiment + language
│     │   ├─ order_service.py          order status/return/query helpers
│     │   ├─ faq_service.py            FAQ matching + self-learning
│     │   ├─ automation.py             proactive background worker
│     │   ├─ ai_service.py             general AI replies
│     │   └─ seed.py                   demo data (1000 orders, 250 customers)
│     ├─ integrations/
│     │   ├─ ai/  (gemini, mock, order_agent [tools], vision)
│     │   └─ whatsapp/ (meta, mock)
│     └─ api/v1/endpoints/         the URLs (chat, webhook, orders, conversations,
│                                  faqs, customers, stats, automation, system)
└─ frontend/                       React dashboard
   └─ src/
      ├─ pages/    Dashboard, LiveChat, InboxPage, Orders, Refunds, FAQs
      ├─ components/  Sidebar, PageHeader, Primitives
      ├─ lib/      ui helpers (colors, formatting), useCountUp
      └─ api.js    all calls to the backend
```

---

## 11. How to run it

Two terminals:

```powershell
# Terminal 1 — backend (http://127.0.0.1:8000, docs at /docs)
cd ai-support-platform\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:5173)
cd ai-support-platform\frontend
npm run dev
```

To use **real Gemini**: put `AI_PROVIDER=gemini` and `GEMINI_API_KEY=...` in `backend/.env`.
To use **real WhatsApp**: see `SETUP_LIVE.md`.

---

## 12. Good questions to ask ChatGPT about this project

- "Explain the difference between the deterministic path and the AI agent path in section 4."
- "Walk me through what happens when a customer sends a damaged-product photo (sections 5–7.6)."
- "Why are refunds human-in-the-loop instead of fully automatic (section 7.4)?"
- "How does the self-learning FAQ loop work end to end (section 7.8)?"
- "How would I switch this from SQLite to PostgreSQL and from mock to real WhatsApp?"

---

*This platform demonstrates a modern, agentic AI support system — comparable to Amazon /
Flipkart / Myntra support, with multi-language, vision, proactive automation, and a
human-in-the-loop safety net.*
