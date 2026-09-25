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

### 1. The database: Neon (free, 5 minutes)

Render's own free database is deleted after 30 days, which would break your
demo while you are still applying for jobs. Neon's free tier does not expire;
it just sleeps when idle and wakes on the next query.

1. Sign up at [neon.tech](https://neon.tech) with your GitHub account
2. Create a project — any name, any region close to you
3. Copy the **connection string**. It looks like:

   ```
   postgresql://user:password@ep-something.region.aws.neon.tech/neondb?sslmode=require
   ```

Keep it somewhere safe for the next step. It contains a password, so it never
goes in the repo — that is exactly why `render.yaml` marks it `sync: false`.

### 2. The app: Render, or Vercel if Render wants a card

Render asks for a card to verify free accounts, and locally issued cards are
often declined. Two ways around it:

- Enable international/online transactions on the card in your bank's app,
  then retry Render, **or**
- Deploy to Vercel's Hobby plan instead, which needs no card. No config file
  is needed: Vercel looks for a FastAPI instance named `app` in `app/main.py`
  and routes every path to it automatically. Adding a catch-all rewrite in
  `vercel.json` actually *breaks* this, because the app then receives the
  rewritten path instead of the real one and matches no route.

  Import the repo at [vercel.com/new](https://vercel.com/new), add the
  environment variables, and create the tables first with:

  ```bash
  DATABASE_URL="<your neon string>" python -m app.init_db
  ```

  Vercel runs the app as serverless functions, so it never sleeps the way
  Render's free tier does, but each request pays a small cold-start cost.

#### Render (free)

1. Sign in to [render.com](https://render.com) with GitHub
2. **New → Blueprint**, pick `link-shortener`; it reads `render.yaml`
3. When it asks for the variables it cannot guess:
   - `DATABASE_URL` — paste the Neon connection string
   - `BASE_URL` — leave blank for now, you do not know the address yet
4. Deploy, and watch the log. The tables are created automatically on first
   start, so there is no database setup to do.

### 3. Tell the app its own address

After the first deploy Render shows your URL, something like
`https://link-shortener-abcd.onrender.com`.

Go to the service's **Environment** tab, set `BASE_URL` to that address (no
trailing slash), and save. Render redeploys automatically.

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

**The first visit is slow.** Free Render services sleep after 15 minutes of no
traffic and take up to a minute to wake. Say so in your README so nobody thinks
the app is broken. If it bothers you later, a free cron service pinging
`/health` every 10 minutes keeps it awake.

**Your local database and the live one are separate.** The account you made on
your laptop does not exist on the live site. Sign up again there.

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
