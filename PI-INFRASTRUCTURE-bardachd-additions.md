# PI-INFRASTRUCTURE.md — additions for Bàrdachd

_The shared `PI-INFRASTRUCTURE.md` is copied verbatim across projects, so rather
than rewrite it, paste these small additions into the matching sections. They
register Bàrdachd as a planned app and reserve its port/path. Do this once,
ideally in the same edit on whichever copy you treat as canonical, then re-share._

---

## 1. Add to the "target architecture" path list

In the `https://ceol-pi.tail01672f.ts.net/…` block, add a Bàrdachd line:

```
https://ceol-pi.tail01672f.ts.net/bardachd/  → Bàrdachd (poetry workshop, FastAPI :8200)
```

---

## 2. Add a per-app note (new subsection under "Per-app notes")

### Bàrdachd — new, build prefix-clean from day one

Bàrdachd (formerly drafted as "Prosody") is a personal poetry-writing workshop:
FastAPI + SQLite, single-page vanilla-JS frontend served from a `frontend.py`
HTML string, no auth (single-user, private behind Tailscale). Internal port
**8200**; to be served at **`/bardachd/`** on the shared **443** Funnel,
following Òrain's proven additive `--set-path` pattern:

```
sudo tailscale funnel --bg --https=443 --set-path=/bardachd http://127.0.0.1:8200
```

**One known migration-tax item to clear before first deploy:** the frontend
currently emits leading-slash absolute API paths (`/api/scan`, `/api/forms`,
etc.), which break under the `/bardachd/` prefix. Per the path-prefix contract
above, the backend stays prefix-naïve (Tailscale strips the prefix) but the
frontend must be made prefix-aware (relative URLs or a JS-derived prefix
constant). This is being fixed in Bàrdachd's own repo before it goes live, so it
arrives prefix-clean and needs no later migration — exactly what this document
asks of new apps. Tracked in `BARDACHD_TODO.md`.

Port check: Ceòl :8001, Shadowing :8003, Òrain :8004 are known internal ports;
8200 is clear but confirm with `ss -ltnp` on the Pi before binding.

---

## 3. (Optional) note in the live-state table

The live-state table records what is *actually running*. Bàrdachd is not deployed
yet, so don't add it as a running row — add it instead to any "planned apps" list
alongside Skywards and Nature Through the Seasons. Once it's live, add a real row:

| `…ts.net/bardachd/` (path on 443) | `127.0.0.1:8200` | `bardachd.service` | **Bàrdachd** poetry workshop |
