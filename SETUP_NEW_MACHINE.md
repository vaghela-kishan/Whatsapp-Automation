# 💻 Running this project on another laptop

A quick, copy-paste guide to move the project to a new machine and run it.

---

## 0. What to send (and what NOT to send)

**DO send** the project folder — but **delete these first** (they are huge and
are re-created automatically on the new machine):

| Delete before zipping | Why | Re-created by |
|---|---|---|
| `frontend/node_modules/` | 100s of MB | `npm install` |
| `backend/.venv/` | 100s of MB, has machine-specific paths | `python -m venv` |
| `backend/dev.db` | demo database | re-seeds on first run |
| `dist/`, `__pycache__/`, `*.log`, `.git/` (optional) | build/cache junk | rebuilt |

> ✅ **Keep `backend/.env`** — it holds your Gemini API key + admin password.
> (If you transfer via GitHub instead, `.env` is *gitignored* and will NOT
> travel — on the new machine copy `backend/.env.example` → `backend/.env`
> and fill in your key + admin credentials.)

The actual source code is only a few MB. Zip it, send via
pen-drive / Google Drive / WhatsApp, and extract on the new laptop.

---

## 1. Install the two prerequisites (once, on the new laptop)

1. **Python 3.13** — https://www.python.org/downloads/
   ⚠️ On the first installer screen, tick **“Add Python to PATH”.**
2. **Node.js (LTS)** — https://nodejs.org/

Verify in a terminal:
```powershell
python --version    # should print 3.13.x
node --version      # should print v20+ or v22+
```

---

## 2. Set up the backend

```powershell
cd ai-support-platform\backend

# create a fresh virtual environment
python -m venv .venv

# activate it (PowerShell)
.venv\Scripts\Activate.ps1
#   (if PowerShell blocks it, run once:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)

# install dependencies
pip install -r requirements.txt
```

Make sure `backend\.env` exists (see step 0). That's it for the backend.

---

## 3. Set up the frontend

```powershell
cd ai-support-platform\frontend
npm install
```

---

## 4. Run it (two terminals)

**Terminal 1 — backend** (seeds 1000 demo orders on first run):
```powershell
cd ai-support-platform\backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```powershell
cd ai-support-platform\frontend
npm run dev
```

Open **http://localhost:5173** and sign in:

```
Username:  admin
Password:  admin123
```

Done — it runs exactly like on the original laptop. ✅

---

## 5. "Live" — three levels

| Level | Who can see it | How |
|---|---|---|
| **Local** | just this laptop | steps above (`localhost`) |
| **Same Wi-Fi** | phones/PCs on your network | run backend/frontend with `--host 0.0.0.0`, open `http://<laptop-ip>:5173` |
| **Public internet** | anyone, anywhere | **deploy** — frontend → Vercel/Netlify, backend → Railway/Render (free tiers). Set `DEBUG=false`, restrict `BACKEND_CORS_ORIGINS`, change `ADMIN_PASSWORD` + `SECRET_KEY` first. |

For a real public demo link (to put on a resume), the **deploy** row is what you
want — ask and I'll walk you through it.

---

## Troubleshooting

- **`python` not found** → reinstall Python with “Add to PATH” ticked, reopen the terminal.
- **`pip install` fails on a package** → make sure you're inside the activated `.venv`.
- **Port already in use** → change `--port 8000` (and update `frontend/vite.config.js` proxy) or close the other process.
- **AI replies in English only / “quota”** → the Gemini free daily limit was hit; it falls back to mock automatically. Fresh quota next day, or switch `GEMINI_MODEL`.
- **Login fails** → confirm `ADMIN_USERNAME`/`ADMIN_PASSWORD` in `backend\.env` match what you type.
