# Tab Command Center (Saidie)

Live: https://saidie-command-center.sites.tab.bot

Phase 1: **Force Respond** buttons (open WhatsApp / iMessage with a wake-up text to Tab) and **live status** of Jena's brain, box tunnel and gateway (`/api/status`, a server-side proxy that returns only safe fields).

Hosting
- `_worker.js` serves it on sites.tab.bot (static assets + `/api/status`).
- `api/status.js` is the same proxy as a Vercel function, so this repo can be connected to the Vercel project `command-center` (Vercel → project → Settings → Git → Connect `pfn000/command-center`, framework "Other"). Every push to `main` then deploys there.
- `.github/workflows/proof.yml` takes 1600x900 and 390x844 screenshots of the live site on every push and commits them to the `proofs` branch.
