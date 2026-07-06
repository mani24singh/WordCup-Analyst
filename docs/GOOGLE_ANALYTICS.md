# Google Analytics 4 (Free) — Setup & Integration

This project includes an **optional, detachable** analytics layer. It uses **Google Analytics 4 (GA4)** on the free tier and sends events from the Streamlit app via the **Measurement Protocol** (server-side). No analytics code runs when keys are missing or `GA_ENABLED=false`.

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

# Optional: also inject browser gtag.js (default false)
GA_CLIENT_INJECT=false
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GA_ENABLED` | No | `true` / `false`. Default `true` if vars set; set `false` to disable without deleting keys |
| `GA_MEASUREMENT_ID` | Yes* | Web stream ID (`G-...`) |
| `GA_API_SECRET` | Yes* | Measurement Protocol secret |
| `GA_CLIENT_INJECT` | No | `true` to add optional client-side gtag snippet |

\*Both required for analytics to activate. If either is empty, the layer is a no-op.

### Streamlit Cloud

In your app dashboard → **Settings** → **Secrets**, add the same variables:

```toml
GA_ENABLED = "true"
GA_MEASUREMENT_ID = "G-XXXXXXXXXX"
GA_API_SECRET = "your_secret"
```

Redeploy after saving secrets.

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