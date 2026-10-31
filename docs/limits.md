# Platform Limits & Engineering Workarounds: RetainAI Console

This document specifies platform boundaries encountered within Streamlit and modern cloud hosting environments, accompanied by our sanctioned, minimal engineering workarounds.

---

## 1. Persistent WebSockets vs. Serverless Hosting (Vercel / Lambda)

### The Limitation
Streamlit is an in-memory, stateful Python server application. It maintains user session state (`st.session_state`) in RAM and relies on an uninterrupted, bidirectional WebSocket channel (`_stcore/stream`) for real-time reactivity (slider adjustments, table row selections, tab toggling). Serverless platforms like **Vercel** or AWS Lambda operate on ephemeral, stateless HTTP request-response cycles with execution timeouts (10–60s) and do not support persistent Python WebSockets. Forcing Streamlit onto Vercel triggers WebSocket disconnections and broken app states.

### Sanctioned Workaround
- **Production Cloud:** Deploy on **Streamlit Community Cloud** (official, free Snowflake runtime), **Render.com**, **Railway.app**, or **Hugging Face Spaces**, which provide persistent Python container execution.
- **Instant Secure Public Tunnel:** Integrated **Cloudflare Tunnel (`cloudflared`)**, exposing the local port via an HTTPS URL (`*.trycloudflare.com`) with QUIC/HTTP2 support and persistent WebSocket streaming.

---

## 2. Glide Data Grid (DataFrame) Theme Synchronization

### The Limitation
Streamlit's `st.dataframe` is rendered using Glide Data Grid on an HTML5 `<canvas>` element inside a Shadow DOM. Canvas elements cannot read runtime CSS custom properties (`var(--color-canvas)`) injected via `<style>` tags. If `.streamlit/config.toml` is unconfigured or set to light mode, `st.dataframe` draws white backgrounds even when dark theme CSS is applied.

### Sanctioned Workaround
- Synchronized `.streamlit/config.toml` to declare `base = "dark"` with terminal tokens (`#0E1217` canvas, `#151B23` panel, `#0E8A73` primary, `#E6EAF0` text).
- Wrapped DataFrame containers with explicit CSS border and panel background rules in `app/ui.py`.

---

## 3. Sidebar Radio Input Bullets

### The Limitation
Streamlit's native `st.sidebar.radio` enforces round circular bullets that resemble consumer survey forms rather than a dense Bloomberg- or Kite-style trading rail.

### Sanctioned Workaround
- Replaced navigation with custom terminal navigation buttons in `render_sidebar_rail()`.
- Implemented state tracking with active left-accent border indicators (`3px solid #0E8A73`), subtle raised background hovers, and live count badges (`18k`, `5`, `0.693`).

---

## 4. Master-Detail Split & Order Ticket Drawer

### The Limitation
Streamlit does not provide a native floating slide-out modal or drawer component.

### Sanctioned Workaround
- Engineered a 65% / 35% responsive master-detail split layout in `app/views/risk_queue.py`.
- Connected `st.dataframe(..., on_select="rerun", selection_mode="single-row")` directly to the right-hand column, which renders an institutional "Intervention Ticket" modeled on a trading order ticket (risk gauge, polarity-split drivers, message preview, and triage action buttons).
