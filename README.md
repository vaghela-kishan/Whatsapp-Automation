# 💬 AI Support Platform — WhatsApp Automation

A beautiful, production-shaped **AI customer-support automation** platform.
Customers message on WhatsApp → the AI detects intent → looks up orders / FAQs →
replies instantly, and escalates to a human only when needed.

```
Customer (WhatsApp)
      │
      ▼
  FastAPI  ──►  Webhook  ──►  AI (intent + reply)  ──►  Database  ──►  Reply
                                     │
                     ┌───────────────┼────────────────┐
                     ▼               ▼                ▼
                Order Status        FAQ          Human Handoff
```

**Runs fully offline in demo mode** — no API keys required. Flip two env vars to
switch to real **Google Gemini** + real **WhatsApp Cloud API**.

---

## ✨ Features

| Area | What it does |
|------|--------------|
| 🤖 **AI replies** | Detects intent (order / FAQ / support / greeting) and answers with the right facts |
| 📦 **Order status** | Looks up an order number (e.g. `AUR-10432`) and returns a rich status + tracking |
| 💡 **FAQ engine** | Token-overlap matcher answers common questions from a managed knowledge base |
| 🤝 **Human handoff** | Complaints / refunds auto-escalate and surface in the agent Inbox |
| 📊 **Dashboard** | Live metrics: volume chart, auto-resolution rate, intents, top FAQs |
| 💬 **Live Chat** | A pixel-accurate WhatsApp simulator with an "AI Insight" side panel |
| 📥 **Inbox** | Agent view of every conversation, with manual reply + resolve |

## 🖥️ Tech stack

- **Backend** — FastAPI · SQLAlchemy 2 · Pydantic v2 · SQLite→Postgres-ready · Alembic
- **Frontend** — React 18 · Vite · Tailwind CSS · Recharts · lucide-react
- **AI** — Google Gemini (pluggable) with a zero-dependency mock engine
- **WhatsApp** — Meta Cloud API (pluggable) with an in-app mock transport

Clean architecture throughout: routes stay thin, logic lives in `services/`,
data access in `crud/`, and every external system sits behind an interface in
`integrations/` — so swapping the AI or WhatsApp provider is a config change,
never a code change.

---

## 🚀 Quickstart

Open **two terminals**.

### 1 · Backend (port 8000)

```powershell
cd ai-support-platform\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

On first run it creates the SQLite database and seeds demo customers, orders,
and FAQs. API docs: <http://127.0.0.1:8000/docs>

### 2 · Frontend (port 5173)

```powershell
cd ai-support-platform\frontend
npm install
npm run dev
```

Open <http://localhost:5173> → try **Live Chat** and ask
_"Where is my order AUR-10432?"_ or _"What is your return policy?"_

---

## 🔌 Going live (optional)

Everything works in mock mode out of the box. To use the real services, edit
`backend/.env`:

**Real AI (Gemini):**
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_from_aistudio.google.com
```

**Real WhatsApp (Meta Cloud API):**
```env
WHATSAPP_PROVIDER=meta
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
```
Then point your Meta app's webhook to `POST /api/v1/webhook/whatsapp`
(verify token = `WHATSAPP_VERIFY_TOKEN`). No code changes needed.

---

## 🧪 Tests

```powershell
cd backend
pytest
```

## 📁 Layout

```
ai-support-platform/
├─ backend/            FastAPI app (see backend/README.md)
│  └─ app/
│     ├─ models/       Customer, Conversation, Message, Order, FAQ
│     ├─ schemas/      Pydantic contracts
│     ├─ crud/         Repositories
│     ├─ services/     intent · faq · order · ai · conversation · stats · seed
│     ├─ integrations/ ai/ (gemini, mock) · whatsapp/ (meta, mock)
│     └─ api/v1/       chat · conversations · orders · faqs · stats · webhook
└─ frontend/           React + Tailwind dashboard
   └─ src/pages/       Dashboard · LiveChat · Inbox · Orders · FAQs
```
