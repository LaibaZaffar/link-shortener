# Roadmap

How this project was built, in the order it happened: a working skeleton, the
features that make it useful, and getting it onto the internet. Each phase is
complete — the notes are kept so the reasoning behind each step is on record.

---

## Phase 0 — Working skeleton ✅ done

Signup and login, create a link, redirect, record clicks, three charts, 23
tests and a CI workflow.

Spend your first session just reading the code and breaking it on purpose.
Change something, run `pytest`, see what fails. That is the fastest way to
understand a codebase you did not write.

---

## Phase 1 — Make it yours ✅ done

- [x] **Copy-to-clipboard button** next to each short link
- [x] **Sort and search** the dashboard: newest, oldest, most clicked, plus a
      search box over code, label and destination
- [x] **QR code** for each link, shown on the stats page and downloadable as PNG
- [x] **Link expiry**: an `expires_at` column; expired links answer `410 Gone`
      with an explanation instead of redirecting
- [x] **Edit a link's destination** without changing its short code
- [x] **Empty state and error polish**: flash messages instead of `?error=` in
      the address bar, a proper "no links yet" state, and a separate message
      for "your search matched nothing"

45 tests now, up from 23 — every feature above arrived with tests covering it.

## Phase 2 — Go live (days 5–7)

This is the phase that matters most. A live URL beats a fourth project.

### 1. The database: Neon (free, 5 minutes)

Neon's free tier does not expire — it sleeps when idle and wakes on the next
query. Render's own free database, by contrast, is deleted after 30 days, which
would quietly break the live demo.

1. Sign up at [neon.tech](https://neon.tech) with your GitHub account
2. Create a project — any name, any region close to you
3. Copy the **connection string**. It looks like:

   ```
   postgresql://user:password@ep-something.region.aws.neon.tech/neondb?sslmode=require
   ```

Keep it somewhere safe for the next step. It contains a password, so it never
goes in the repo. It is set as an environment variable on the host instead.

### 2. The app: Vercel (free)

Render was the first choice, but its free tier requires card verification and
the card was declined — a common problem with cards that block international
transactions by default. Vercel's Hobby plan needs no card, so that is where
this ended up.

1. Sign in to [vercel.com](https://vercel.com) with GitHub
2. Import the repository. No config file is needed: Vercel looks for a FastAPI
   instance named `app` at conventional entrypoints, and `app/main.py` is one
   of them
3. Add three environment variables:
   - `DATABASE_URL` — the Neon connection string
   - `SECRET_KEY` — generate one with
     `python -c "import secrets; print(secrets.token_hex(32))"`
   - `BASE_URL` — leave empty until the first deploy finishes
4. Create the tables before the first visit:

   ```bash
   DATABASE_URL="<your neon string>" python -m app.init_db
   ```

Do **not** add a catch-all rewrite in `vercel.json` pointing at an entrypoint.
Vercel now passes the rewritten path to the app, so FastAPI receives
`/api/index` for every request, matches no route and returns 404 on everything.
The fix was deleting that config, not adding to it.

### 3. Tell the app its own address

After the first deploy Vercel shows the URL, something like
`https://link-shortener-43dv.vercel.app`.

Go to Settings → Environment Variables, set `BASE_URL` to that address (no
trailing slash), and redeploy so the new value takes effect.

Skipping this is the single most common mistake here: the app would keep
displaying your short links as `http://127.0.0.1:8000/abc123`, which works for
nobody but you.

### 4. Check it properly

- Visit `/health` — it should answer `{"status": "ok"}`
- Sign up on the live site, create a link, click it, refresh the stats page
- Check the chart moved and the short link shows your real domain

### 5. Finish the repo

- Put the live URL at the top of `README.md`, replacing the placeholder
- Add a screenshot to `docs/screenshot.png` — most people reading your repo
  will never run the code
- Prove CI works: push a commit that breaks a test on a branch, watch the
  GitHub Actions run go red, fix it, watch it go green

### Things that will surprise you

**The first visit is slow.** Serverless functions start on demand, so the first
request after a quiet period spends about a second waking up. Everything after
that is fast. Say so in the README, so nobody assumes the app is broken.

**Your local database and the live one are separate.** The account you made on
your laptop does not exist on the live site. Sign up again there.
