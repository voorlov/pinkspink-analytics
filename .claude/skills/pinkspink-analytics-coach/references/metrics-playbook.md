# Metrics Playbook — Pinkspink

This reference is loaded only when needed. It explains what each block on the dashboard means, what counts as a meaningful move, and how to avoid over-interpreting noise at current volumes.

## Small-sample reality check (read first, every time)

Pinkspink is at sub-thousand sessions/week scale. At this volume, classical "X% change" thinking will lie to you constantly. Before reporting any change as significant, apply these rules:

**Absolute floor for percentage metrics:** A change in a rate (ATC rate, scroll rate, conversion) is only worth mentioning if BOTH:
- The numerator is ≥ 10 events in both periods being compared, AND
- The relative change is ≥ 25 percentage points OR the absolute count of events doubled / halved.

**Absolute floor for volume metrics:** Sessions, users, pageviews — only mention a change if the absolute delta is ≥ 50 sessions or ≥ 30%, whichever is greater.

**Single-day events:** Do not report on single-day-only spikes unless they sustain into the next day. One-day-only patterns are usually one of: a bot, a single influencer mention, an ad campaign first day, or a friend posting the link in a chat.

**The "1 purchase" trap:** Until purchase count crosses 5/week, do not compute or report any metric that has purchase in the denominator or numerator (revenue per session, AOV, conversion rate at last step). State explicitly: "purchase volume too low for stable metrics this week".

When in doubt, say "no signal yet" instead of inventing one.

## Block-by-block guide — Сводка tab

**KPI row (top, 5 tiles):** RPS, Revenue, ATC rate, Purchase rate, Cart-to-Purchase. Compared vs avg of 4 previous weeks.
- *What to actually use*: ATC rate is the only one with enough volume to be reliable. The other four are noise until purchase count grows.
- *Watch for*: ATC rate moving more than ±25% relative — that's a real signal.

**Visitors and sessions (sum):** Total volume. Use as the denominator sanity check before interpreting any rate.

**Sessions by device:** Mobile/Desktop/Tablet split. Pinkspink is mobile-dominant (~70%+). A shift toward desktop usually means a referral surge (PR mention, B2B link) or that Social traffic dropped.

**New vs Returning:** Returning users are the leading indicator of brand strength at this stage. A returning-share trending up is one of the few genuinely positive signals possible right now.

**Time on site (median, sec):** Median is the right central measure here (mean is destroyed by bots). Healthy = 30+ sec. <15 sec = bounce-heavy week.

**Bounce rate:** Useful as a paid-traffic-quality signal more than anything else. Site-wide bounce is dominated by Paid. If site-wide bounce drops noticeably, the cause is usually that Paid traffic share dropped, not that engagement improved.

**Источник трафика (Traffic source) chart + table:** Channel × period view. The table is sortable and is the single most useful block on the Сводка tab for diagnosing "what changed". Always look at it before forming hypotheses.

**Посетители по странам:** Top countries by sessions. Look for new entrants in top-10 (means a campaign or organic discovery in a new geo).

**ATC Rate + Purchase Rate:** Site-wide rates. Same caveat as KPI tiles — Purchase rate is too noisy.

**Рейтинг ATC top-10 / Рейтинг Purchase Rate top-10:** These are by what — product? source? country? Check the actual chart legend in the report. Top-10 lists are useful for finding outlier good performers worth investigating.

**Scroll Rate (by device, by channel):** % of sessions reaching scroll-90% on any page. Healthy mobile is hard to define yet — establish a baseline and watch for moves.

**Cohort Retention:** Returning user behavior by signup-week cohort. Week 0 is hidden by default. Useful for monthly reports, not daily.

## Block-by-block guide — Воронки tab

**Динамика воронок по устройствам — sessions (top row):** Mobile and desktop funnel volumes side-by-side. Read this as 6 bars per device: home → catalog → product → ATC → checkout → purchase. The shape of the drop-off tells you which stage broke.

**Динамика воронок по устройствам — конверсии (bottom row):** Same funnel but as conversion rates between consecutive stages. The View→ATC step is the one to watch — that's where the 98% loss lives.

**Кто добавляет в корзину и покупает (table):** Country + source rows of who actually got to ATC/checkout/purchase. At current volumes, this table will have very few rows — that's normal. Each row is precious data.

**Эффективность каналов по этапам (4 bubble charts):** Catalog→Product, Product→Cart, Cart→Checkout, Checkout→Purchase.
- X-axis = sessions at the stage (volume), Y-axis = conversion to next stage, bubble size = sessions.
- Read these as a 2×2: top-right = high volume + high conversion = your best channel for this step. Bottom-right = high volume + low conversion = your biggest leak. Top-left = high quality but low volume = scale candidate.
- Color zones (green/yellow/red) are heuristic, not validated for Pinkspink yet. Trust position over color.

**Эффективность по странам (4 bubble charts):** Same logic, but for top-10 countries.

## Block-by-block guide — Карточка товара tab

**Время на одной карточке товара:** Time spent per product page view. Useful for distinguishing "people are interested but not buying" (high time, low ATC = pricing/sizing/shipping objection) from "people leave fast" (low time = wrong-fit traffic).

**Карточек за сессию — разрез по странам и source:** How many products people browse per session. <2 = window-shoppers. 4+ = engaged. Source/country breakdown reveals which traffic actually shops.

**Топ-30 карточек товара:** Bestseller list by views. Watch for movers week-over-week.

**Время на товарных страницах (сессия целиком):** Total time spent on product pages per session.

**Scroll на странице товара:** % of product-page sessions reaching scroll-90%. If low — product page below-the-fold content is being missed (descriptions, sizing, reviews).

**Глубина каталога:** How deep into category pages users go. Useful for understanding catalog UX problems.

## Comparison logic — what against what

| Cadence | Compare to | Why |
|---|---|---|
| Daily | Trailing 7-day average | Day-over-day too noisy at this volume |
| Weekly (Mon–Sun) | Average of previous 4 full weeks | Already implemented in dashboard ("vs avg 4 прошлые недели") |
| Monthly | Previous full month | Standard, but call out when month length differs |

Never compare a partial week or partial month — wait until the period is closed.

## Glossary of metric names you'll see

- **RPS** — Revenue per session (sum revenue / sum sessions). Meaningless at <5 purchases/week.
- **PR** — Purchase rate (sessions with purchase / total sessions).
- **C2P** — Cart-to-purchase (sessions with purchase / sessions with ATC). Key efficiency metric for the bottom of the funnel.
- **ATC rate** — Add-to-cart rate (sessions with ATC / total sessions).
- **ER** — Engagement rate (GA4 definition: sessions ≥10s OR ≥2 pageviews OR a conversion event).
- **Median sec** — Median time on site in seconds.
- **Глубина 2+** — Sessions with 2+ pageviews / total sessions.

## Anti-patterns (do not do these)

- Do not compute month-over-month for any metric where the numerator was <30 in either month.
- Do not interpret bounce rate without also stating the source channel split — site-wide bounce is dominated by Paid.
- Do not say "conversion improved" without specifying which step. The funnel has 5 conversion steps and they move independently.
- Do not blame "the algorithm" (Instagram, Meta Ads, Google) without first checking whether traffic volume changed. Most "algorithm" stories are actually self-inflicted (creative ran out, audience saturated, ad spend changed).
- Do not include the excluded countries (CN/HK/KR/SG) in customer-facing analysis. Owners' VPN traffic.
