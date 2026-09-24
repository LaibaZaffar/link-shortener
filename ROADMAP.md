# Roadmap

Everything in **Phase 0** is already written and passing tests. Phases 1 and 2
are the parts to do yourself — that is where the learning (and the interview
answers) come from. Phase 3 is optional polish that makes the CV line stronger.

Suggested pace: about two weeks at a couple of hours a day.

---

## Phase 0 — Working skeleton ✅ done

Signup and login, create a link, redirect, record clicks, three charts, 23
tests, Docker file, CI workflow, Render blueprint.

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

43 tests now, up from 23. "I test my own code" is a genuinely uncommon thing on
a junior CV.

### Ideas if you want more practice here

- [ ] Keep what the user typed when a form is rejected (right now the boxes clear)
- [ ] Bulk delete with checkboxes
- [ ] Pagination once a user has more than ~50 links
- [ ] Show the expiry as a countdown ("expires in 6 days") rather than a date

---

## Phase 2 — Go live (days 5–7)

This is the phase that matters most. A live URL beats a fourth project.

1. **Put it on GitHub**

   ```bash
   git init
   git add .
   git commit -m "Link shortener with click analytics"
   git branch -M main
   git remote add origin https://github.com/<your-username>/link-shortener.git
   git push -u origin main
   ```

   Check that `.env` did **not** get committed — `.gitignore` already excludes
   it, but look anyway. Leaked secrets are a bad first impression.

2. **Deploy on Render** (free tier, no card needed)

   - Sign in to [render.com](https://render.com) with GitHub
   - **New → Blueprint**, pick your repo; it reads `render.yaml` and creates
     both the web service and a PostgreSQL database
   - After the first deploy, copy your live URL (e.g.
     `https://link-shortener-abcd.onrender.com`) into the `BASE_URL`
     environment variable, then redeploy

   Two things to know about the free tier: the app sleeps after ~15 minutes of
   no traffic and takes a few seconds to wake up, and free databases are
   deleted after 30 days, so re-create it if you leave the project alone.
   Mention the sleep in your README so a recruiter is not confused by a slow
   first load.

3. **Check the deploy is healthy**: visit `/health`, sign up on the live site,
   create a link, click it, confirm the chart moves.

4. **Prove CI works**: push a commit that breaks a test on a branch, watch the
   GitHub Actions run go red, fix it, watch it go green. Then add the badge to
   your README:

   ```markdown
   ![tests](https://github.com/<your-username>/link-shortener/actions/workflows/ci.yml/badge.svg)
   ```

5. **Add a screenshot** to `docs/screenshot.png`. Most people looking at your
   repo will never run the code.

---

## Phase 3 — The parts that impress (days 8–14, pick one or two)

Do **not** do all of these. One finished feature explained well beats four
half-built ones.

- [ ] **Redis caching on the redirect.** Every visit currently hits the
      database to look up the code. Cache `code → destination` in Redis, and
      you can say "cut redirect latency from ~40ms to under 5ms" with numbers
      you measured yourself. This is the single best talking point in the
      project. (`pip install redis`; Render offers a free Redis instance.)
- [ ] **Rate limiting** on link creation, so one user cannot make 10,000 links.
- [ ] **A REST API with token auth** alongside the web pages, so the project
      demonstrates both server-rendered HTML and a JSON API.
- [ ] **Database migrations with Alembic**, instead of creating tables on
      startup. This is how real teams change a schema without losing data.
- [ ] **Country-level stats** using a GeoIP lookup of the visitor's IP.

---

## What to say in an interview

Have a real answer ready for each of these. They will get asked.

- *Why store one row per click instead of a counter?* Because a counter can
  only answer "how many". Events answer "when, from where, on what".
- *What happens if two random codes collide?* The code checks the database and
  generates another; the `code` column is also `unique`, so the database is the
  final safety net.
- *Why is the code column indexed?* Every redirect is a lookup by code. Without
  an index the database scans the whole table, which gets slower as you grow.
- *How are passwords stored?* PBKDF2-SHA256 with a random per-user salt, the
  same algorithm Django uses by default. Never the password itself.
- *How do you stop one user reading another's stats?* Every route that loads a
  link checks `link.user_id` against the logged-in user before showing anything.

## Resume bullet to adapt

> **Shortly — link shortener with analytics** (FastAPI, PostgreSQL, Docker) ·
> *live demo · source*
> Built and deployed a full-stack link shortener with user accounts, custom
> short codes, and a click-analytics dashboard charting traffic by day,
> referrer, and browser. Covered core logic with 23 pytest tests running in
> GitHub Actions CI.
