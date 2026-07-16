# 🚀 Go Live — Real Gemini AI + Real WhatsApp

This guide takes the platform from **demo mode** (mock AI + mock WhatsApp) to a
**live automation** answering real customers on WhatsApp with real AI. The code
is already written — you only add credentials.

All settings below go in **`backend/.env`**. Restart the backend after changes.

---

## Part 1 · Real AI with Google Gemini  ⏱️ ~5 min · Free

### 1. Get an API key
1. Go to **<https://aistudio.google.com/app/apikey>**
2. Sign in with a Google account → **Create API key** → copy it.

### 2. Configure the backend
In `backend/.env`:
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=paste_your_key_here
GEMINI_MODEL=gemini-1.5-flash
```

### 3. Restart & verify
```powershell
# restart uvicorn, then:
curl "http://127.0.0.1:8000/api/v1/system/ai-test?q=Hi, are you live?"
```
You should get a natural Gemini reply and `"provider": "gemini"`.
Also check the dashboard sidebar — it now says **“gemini · online”**.

> 💡 The assistant's name, tone, and business facts come from `BUSINESS_NAME`,
> `ASSISTANT_NAME`, `SUPPORT_HOURS` in `.env`. Order-status and FAQ answers stay
> fact-accurate (served from your DB); Gemini handles greetings, unknown
> questions, and empathetic phrasing.

If the key is missing/invalid the app **automatically falls back to the mock
engine** — it never crashes.

---

## Part 2 · Real WhatsApp with Meta Cloud API  ⏱️ ~30 min · Free tier

You need: a **Facebook account**, a **Meta Business** account, and a phone
number for the *test* sender (Meta provides one free).

### 1. Create the app
1. Go to **<https://developers.facebook.com/apps>** → **Create App**.
2. Choose use case **“Other”** → type **“Business”** → name it.
3. In the app dashboard, find **WhatsApp** → **Set up**.

### 2. Grab your credentials
From **WhatsApp → API Setup** you'll see:
- **Temporary access token** (valid 24h) → `WHATSAPP_ACCESS_TOKEN`
- **Phone number ID** (under the test number) → `WHATSAPP_PHONE_NUMBER_ID`
- Add **your own phone number** as a recipient (required for test mode) and
  verify the OTP.

From **App Settings → Basic**:
- **App Secret** → `WHATSAPP_APP_SECRET`

### 3. Expose your local server (for testing)
Meta must reach your webhook over HTTPS. For local dev use **ngrok**:
```powershell
# install from https://ngrok.com/download, then:
ngrok http 8000
```
Copy the `https://xxxx.ngrok-free.app` URL it prints.

> In production, use your deployed HTTPS URL instead of ngrok.

### 4. Configure the webhook in Meta
In **WhatsApp → Configuration → Webhook → Edit**:
- **Callback URL:** `https://xxxx.ngrok-free.app/api/v1/webhook/whatsapp`
- **Verify token:** the same value as `WHATSAPP_VERIFY_TOKEN` in your `.env`
  (default `dev-verify-token`)
- Click **Verify and save** — Meta calls your `GET` endpoint and it responds. ✅
- Under **Webhook fields**, click **Manage** → **Subscribe** to **`messages`**.

### 5. Configure the backend
In `backend/.env`:
```env
WHATSAPP_PROVIDER=meta
WHATSAPP_VERIFY_TOKEN=dev-verify-token
WHATSAPP_ACCESS_TOKEN=your_temporary_or_permanent_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_APP_SECRET=your_app_secret
```
Restart the backend. The sidebar should now read **“WA · meta”**.

### 6. Test it live 🎉
From **your** WhatsApp, message the test number (or reply to the template Meta
sends). Try:
> *Where is my order AUR-10432?*

The AI replies on real WhatsApp, and the message appears in your **Inbox** and
**Dashboard** in real time.

### 7. Going to production
- **Permanent token:** create a **System User** in Meta Business Settings and
  generate a non-expiring token (the API-Setup token lasts only 24h).
- **Verify your business** and add a **real phone number** to message any
  customer (test mode only messages numbers you've added).
- **Message templates:** to start a conversation (vs. reply within 24h) you must
  use an approved template.

---

## Quick reference — `.env` for full live mode

```env
# AI
AI_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash

# WhatsApp
WHATSAPP_PROVIDER=meta
WHATSAPP_VERIFY_TOKEN=dev-verify-token
WHATSAPP_ACCESS_TOKEN=EAAG...
WHATSAPP_PHONE_NUMBER_ID=1234567890
WHATSAPP_APP_SECRET=abc123...

# Recommended for production
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/support
ENVIRONMENT=production
DEBUG=false
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `system/ai-test` still says `provider: mock` | Key missing/invalid, or `AI_PROVIDER` not `gemini`. Check backend logs for `ai_provider_gemini_unavailable`. |
| Webhook “Verify and save” fails | `WHATSAPP_VERIFY_TOKEN` in `.env` must exactly match the token typed in Meta; backend must be reachable over HTTPS. |
| Messages not arriving | Ensure you **subscribed to `messages`** field; check ngrok is running; watch backend logs for `webhook_processed`. |
| `403 invalid signature` | `WHATSAPP_APP_SECRET` doesn't match the app. Clear it to disable verification while debugging. |
| Reply not delivered | Token expired (24h test tokens) or recipient not added in test mode. |
