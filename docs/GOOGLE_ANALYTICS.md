# Google Analytics 4 (Free) — Setup & Integration

This project includes an **optional, detachable** analytics layer. It uses **Google Analytics 4 (GA4)** on the free tier with two channels:

1. **Browser gtag.js** — so Google's *"tag detected on your website"* check passes (injected into the Streamlit parent page).
2. **Measurement Protocol** (server-side) — detailed custom events (briefing generated, downloads, errors).

No analytics runs when `GA_ENABLED=false` or keys are missing.

---

## What you can measure (no personal API keys stored)

GA4 will show aggregated usage such as:

| Insight | Source |
|---------|--------|
| Active users, sessions, engagement time | GA4 reports |
| Country / region / city (approximate) | GA4 geo report (from request IP) |
| Device category, OS, browser | GA4 tech report |
| Custom events | This app (see below) |

### Custom events sent by WorldCup Analyst

| Event | When | Parameters |
|-------|------|------------|
| `page_view` | Once per browser session | page title |
| `session_context` | Once per session | which key slots are filled (boolean only) |
| `keys_missing` | User clicks Generate without required keys | missing key names |
| `briefing_requested` | Valid generate click | query length (not the query text) |
| `briefing_generated` | Successful briefing | team name, corrected flag, match found, briefing size |
| `briefing_error` | Exception or team resolve failure | error category |
| `setup_guide_download` | API setup .docx downloaded | asset name |
| `briefing_download` | Briefing .docx downloaded | team name |

**Privacy:** User API keys and raw queries are **never** sent to Google.

---

## Step 1 — Create a free Google Analytics account

1. Go to [https://analytics.google.com/](https://analytics.google.com/)
2. Sign in with a Google account
3. Click **Start measuring** (or **Admin** → **Create account** if you already use GA)
4. **Account name:** e.g. `WordCup Analyst`
5. Configure data-sharing options as you prefer → **Next**
6. **Property name:** e.g. `WordCup Analyst Streamlit`
7. **Reporting time zone** and **Currency** → **Next**
8. **Industry** and business size (any reasonable choice) → **Create**
9. Accept the Terms of Service

---

## Step 2 — Create a Web data stream (get Measurement ID)

1. In GA4, open **Admin** (gear icon, bottom left)
2. Under **Property**, click **Data streams**
3. Click **Add stream** → **Web**
4. **Website URL:** `https://wordcup-analyst-2026.streamlit.app` (or your Streamlit URL)
5. **Stream name:** `Streamlit App`
6. Click **Create stream**
7. Copy the **Measurement ID** — format: `G-XXXXXXXXXX`

This is your `GA_MEASUREMENT_ID`.

---

## Step 3 — Create a Measurement Protocol API secret

Server-side events require an API secret (still free):

1. On the same **Web stream** details page, scroll to **Measurement Protocol API secrets**
2. Click **Create**
3. **Nickname:** e.g. `streamlit-server`
4. Click **Create**
5. Copy the **Secret value** (shown once)

This is your `GA_API_SECRET`.

---

## Step 4 — Add keys to `.env`

Copy from `.env_example` and set:

```env
# Google Analytics 4 (optional — leave blank to disable)
GA_ENABLED=true
GA_MEASUREMENT_ID=G-XXXXXXXXXX
GA_API_SECRET=your_measurement_protocol_secret

# Browser gtag (default true — needed for Google's tag detection wizard)
GA_CLIENT_INJECT=true
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GA_ENABLED` | No | `true` / `false`. Set `false` to disable without deleting keys |
| `GA_MEASUREMENT_ID` | Yes† | Web stream ID (`G-...`) — **required for gtag detection** |
| `GA_API_SECRET` | Yes‡ | Measurement Protocol secret — for server custom events |
| `GA_CLIENT_INJECT` | No | Default `true`. Injects gtag into the page. Set `false` to disable browser tag only |

†Minimum for Google's tag checker to pass.  
‡Required for server-side custom events (`briefing_generated`, etc.). Tag detection works without it.

### Streamlit Cloud

In your app dashboard → **Settings** → **Secrets**, add the same variables:

```toml
GA_ENABLED = "true"
GA_MEASUREMENT_ID = "G-XXXXXXXXXX"
GA_API_SECRET = "your_secret"
GA_CLIENT_INJECT = "true"
```

Redeploy after saving secrets.

---

## Troubleshooting: "Your Google tag wasn't detected"

Google's setup wizard looks for **gtag.js on the live page**. Streamlit hides normal `<script>` tags inside iframes, so a basic embed will fail detection.

**This project fixes that** by injecting gtag into `window.parent.document` (see `app/analytics/gtag.py`).

### Checklist

1. **`GA_MEASUREMENT_ID` is set** in Streamlit Cloud **Secrets** (not only locally in `.env`).
2. **`GA_CLIENT_INJECT` is not `false`** (default is `true`).
3. **Redeploy** the app after changing secrets (Settings → Secrets → Save → Reboot app).
4. Open your live URL: `https://wordcup-analyst-2026.streamlit.app/`
5. Wait 10–20 seconds on the page, then run Google's tag checker again.

### Verify in browser DevTools

1. Open the live app → **F12** → **Network** tab
2. Filter by `gtag` or `google`
3. You should see a request to `googletagmanager.com/gtag/js?id=G-XXXXXXXXXX`

### If still not detected

- Confirm the Measurement ID matches the **Web** data stream for your Streamlit URL (not an old test stream).
- Try **GA4 → Admin → Data streams → your stream → View tag instructions** and compare the `G-` ID.
- Use **Realtime** report instead of the wizard: open the app in another tab; Realtime should show 1 active user within 30s if gtag works.

Server-only events (`GA_API_SECRET`) do **not** satisfy Google's tag wizard — you need `GA_MEASUREMENT_ID` + client inject.

---

## Step 5 — Verify events

### Option A — GA4 Realtime report

1. Open GA4 → **Reports** → **Realtime**
2. Run the app and click **Generate briefing**
3. Within ~30 seconds you should see active users and custom events

### Option B — DebugView (optional)

1. GA4 **Admin** → **DebugView** (under Property)
2. Temporarily set in `.env`: use GA debug endpoint by sending a test from [Google's event builder](https://developers.google.com/analytics/devguides/collection/protocol/ga4/verify-implementation)

### Option C — Debug endpoint (developers)

```bash
curl -X POST "https://www.google-analytics.com/debug/mp/collect?measurement_id=G-XXX&api_secret=YYY" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"test-1","events":[{"name":"test_event","params":{"source":"manual"}}]}'
```

Check the JSON response for validation messages.

---

## Where the code lives (detachable layer)

```
app/analytics/
├── __init__.py           # public exports
├── settings.py           # reads GA_* from environment
├── client.py             # Measurement Protocol HTTP sender
├── gtag.py               # Parent-frame gtag injector (tag detection)
└── streamlit_bridge.py   # Streamlit hooks + event helpers
```

Integration points (only in `streamlit_app.py`):

```python
from app.analytics import get_analytics

analytics = get_analytics()
analytics.bind_session()
# ... track_* calls on user actions
```

---

## How to disable or remove analytics

### Temporary off (keep code)

```env
GA_ENABLED=false
```

Or remove `GA_MEASUREMENT_ID` and `GA_API_SECRET`.

### Full removal

1. Delete the `app/analytics/` folder
2. Remove `from app.analytics import get_analytics` and all `analytics.*` calls from `streamlit_app.py`
3. Remove `GA_*` variables from `.env` and Streamlit secrets

The rest of the app works unchanged.

---

## Useful GA4 reports after data collects

- **Reports → Engagement → Events** — counts per custom event
- **Reports → User → Demographics** — country / city
- **Reports → Tech → Tech details** — device & browser
- **Explore** — build funnels: `page_view` → `briefing_requested` → `briefing_generated`

Allow 24–48 hours for full standard reports; Realtime works immediately.

---

## Limits (free tier)

GA4 free is suitable for this app’s traffic. Very high event volumes may hit quotas; the app sends only a handful of events per session. See [Google Analytics limits](https://support.google.com/analytics/answer/11202813) for current documentation.