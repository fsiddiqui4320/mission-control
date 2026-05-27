# Mission Control — Deploy Notes

## How to Deploy

**Just push to main.** Vercel GitHub integration auto-deploys.

```
git push origin main
```

That's it. No `vercel --prod`. No `vercel deploy`.

## Setup

- **GitHub**: https://github.com/fsiddiqui4320/mission-control
- **Vercel project**: mission-control (linked to GitHub)
- **Production domains**: set via Vercel dashboard
- **GitHub integration**: auto-deploys on push to `main`

## ❌ Do NOT

- Run `vercel --prod` or `vercel deploy` — creates competing CLI-sourced deployments
- Use `vercel env add` interactively — use Vercel REST API or dashboard

## Architecture Note

This is a local-first dashboard. The Python server (`server.py`) reads Octo's filesystem and serves JSON.  
On Vercel, the static frontend falls back to demo data after 1.5s.

To run locally with live data: `python server.py` → open `http://localhost:5555`
