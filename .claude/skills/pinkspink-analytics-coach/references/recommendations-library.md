# Recommendations Library — Pinkspink

A reference of recommendation patterns calibrated for Pinkspink's current stage (very low purchase volume, mobile-dominant, Shopify, Instagram-driven). Use these as anchors — adapt to the specific data, do not copy verbatim.

The library is organized by which dashboard signal triggers the recommendation.

## Format reminder

Every recommendation should fit this shape:
> **[Action verb + specific change]**, motivated by [block in dashboard / specific metric move]. Expected to move [target metric] by [rough magnitude]. Implementation: [hours / days / weeks]. Risk: [low / medium / high].

If you can't fill all five fields with a straight face, the recommendation isn't ready.

---

## Triggers and recommendations

### Trigger: View→ATC stays at <3% on mobile

The biggest standing problem. Highest-leverage tests:

1. **Sticky ATC button on mobile product pages.** Currently the ATC button is below the gallery, requires scrolling. Theme edit in Shopify, ~1 day. Expected: View→ATC mobile +0.5–1pp. Risk: low.

2. **Move size selector above the fold on mobile.** Users dropping before they reach sizing means they don't even know the product exists in their size. Theme edit, ~half day. Expected: scroll-90% on product pages goes up, ATC on mobile +0.3–0.7pp. Risk: low.

3. **Add free-shipping threshold or shipping cost preview on product page.** Shipping shock is a top reason for ATC abandonment in cross-border ecommerce. Shopify app or theme edit, 1–2 days. Expected: ATC rate +0.5pp. Risk: low.

Avoid: redesigning the whole product page, redoing the brand. Too expensive, too slow to validate at this volume.

### Trigger: Paid (Meta Ads) bounce stays >80% and median <15s

The standing problem with Paid. Order of triage:

1. **Pause the worst-performing ad set for one week.** Use the Эффективность каналов bubble chart on Воронки tab — Paid sits in the bottom-right (high volume, near-zero conversion). Pausing isolates whether site behavior improves with less Paid pollution. Implementation: 5 minutes in Ads Manager. Expected: site-wide bounce drops 5–10pp without losing meaningful purchases. Risk: low (we can un-pause).

2. **Audit landing page match.** If Paid sends users to homepage but our hypothesis is "mobile users skip homepage", there's a basic UX mismatch. Send Paid to specific collection or product. Implementation: 1 day to set up + creative variant. Expected: Paid bounce −15pp, time-on-site +10s. Risk: medium (creative might not convert).

3. **Stop Paid entirely for 2 weeks, compare site economics.** Drastic but fast-learning. If purchases don't drop in those 2 weeks, Paid was buying nothing. Implementation: instant. Risk: medium (FOMO of "what if it was working slightly").

### Trigger: New entrant in top-10 countries

Someone we weren't targeting started showing up. Pattern:

1. **Drill into source × country.** Was it Direct (mention in a Telegram chat?), Referral (PR), Social (an influencer reposted in that geo)? Run a one-off SQL to find the originating source.

2. **Don't act until 2 weeks of data.** Single-week new entrants are noise.

3. **If sustained: consider a soft local touch.** Currency display, language nudge, payment methods for that geo. In Shopify, currency switching is a free app. Implementation: 1 day. Risk: low.

### Trigger: Returning users share trending up

Genuinely positive signal at this stage. Recommendations are about leaning into it:

1. **Create a 3-email Omnisend flow for second-visit users.** Implementation: 2 days. Expected: returning user purchase rate goes from "noise" to "measurable" within 4 weeks. Risk: low.

2. **Add a soft retention CTA on Thank-You page** (newsletter / Instagram follow). 1 day. Risk: low.

### Trigger: Specific product climbs Топ-30 unexpectedly

A leading indicator of demand pattern.

1. **Bring it to the homepage and a Story.** Cheap, fast. Implementation: 1 hour. Risk: zero.

2. **Stock + variant audit.** Make sure popular sizes aren't out of stock before promoting harder.

3. **Wait for week-2 confirmation before bigger moves** (paid promotion of that SKU, dedicated content).

### Trigger: Scroll rate drops site-wide

Usually signals a bad week of traffic quality, not a UX regression. Order:

1. **First check channel mix.** A surge in Paid would drag scroll down without anything actually breaking. If channel mix is stable — investigate the page-level scroll on Карточка товара tab to see if the drop is product-page-specific.

2. **Check for recent theme deploy.** Did anything change in the site code in the last 7 days?

### Trigger: Cohort retention curve worsening

Long-horizon signal, only investigate from monthly reports.

1. **Look at signup-week cohort × source.** Is one acquisition channel producing low-retention users? Often Paid does this.

2. **Talk to the user about brand / product positioning** — at this stage, retention is mostly product, not site UX. Recommendations here cross over from analytics into business strategy. Be careful about overstepping.

### Trigger: A segment with quality index ≥1.5× site-wide is found

The strategically most important pattern for Pinkspink at this stage. Ads currently run on Japan, but if the data reveals a segment with better unit-economics, that's a potential pivot or expansion.

Full recommendation workflow:

1. **Confirm the segment.**
   - Volume: ≥10 sessions in the period, ideally confirmed by a second week.
   - Confounder check is mandatory: is it not the team's VPN (see exploration-patterns.md § C1)? Not bots? Not a one-off IG repost? Run through the Confounders catalog and explicitly confirm the segment is clean.

2. **Quantitative measurement.**
   - Segment ATC rate vs site-wide.
   - Median engagement (sec) for segment vs site-wide.
   - Avg pageviews/session for segment vs site-wide.
   - Returning user share in the segment (if available).

3. **Compare to current primary ad target.**
   - Same metrics for Japan over the same period.
   - If the segment beats Japan on 2+ of the 4 metrics — serious expansion candidate.

4. **Hypothesis for why the segment works.**
   - More affluent audience?
   - Familiar with cross-border e-commerce?
   - Product style/aesthetic fits a local fashion moment?
   - Niche with no local competition?

5. **Minimum viable test.**
   - Budget: $50–200 for first validation. Don't reallocate 50% of spend immediately — even a confirmed segment behaves differently at scale.
   - Duration: 2 weeks minimum.
   - Creative: the one that works best on the current target (isolate the "geo" variable, don't change everything at once).
   - Landing: ensure the country sees the right currency (Shopify → Markets), and language if needed. Without this the test is uninformative.
   - Success metric: ATC rate in the test segment ≥1.5× the current Japan ATC rate.

6. **Post-test.**
   - On success: scale to 30% of Paid budget on the new segment, continue testing further.
   - On failure: understand why (bad creative? bad landing? test too short? confounder in the source data?). Do not discard the segment immediately.

Specific segments currently in focus for Pinkspink (as of skill creation):

- **🇺🇸 USA** — the user explicitly flagged this as a stated hypothesis. High engagement noted in data. Every weekly report must explicitly check USA against the quality index and explicitly report status.
- **🇩🇪 Germany, 🇳🇱 Netherlands, 🇫🇮 Finland** — mentioned as "high ER at low volume". Volume not yet enough for a test, but if any crosses 10 sessions/week with good engagement — it's a candidate.
- **City-level inside USA** — should be checked separately. Not all of USA is the same. NY, LA, Bay Area can behave like three different segments.

Anti-pattern: recommending expansion to "USA as a whole" when 80% of high-quality USA traffic comes from one city. Always drill one level deeper than country.

---

## Generic patterns (apply broadly)

### Test, don't redesign
At Pinkspink's volume, a full redesign won't be statistically observable for months. Recommend small, isolated tests with measurable outcomes. Even if the test is "wrong", you learn something.

### Mobile-first, always
Mobile is 70%+ of traffic. Any recommendation that's "desktop-first" or "looks great on desktop" is misallocated effort. Always specify the mobile implementation first.

### Shopify-native is cheaper than custom
The store is on Shopify. Recommendations that use built-in features or marketplace apps have implementation cost in hours. Custom code recommendations have implementation cost in weeks. Prefer the former unless the latter is clearly better.

### Don't recommend ad spend increases
At current conversion rates, more ad spend = more wasted ad spend. The bottleneck is the site, not the funnel input. Until ATC rate doubles, do not recommend spending more on ads.

### Honesty about purchase data
Until purchases hit 5+/week, almost all "purchase-driven" recommendations are guessing. Be explicit: "this recommendation assumes Y, which we'll only validate once purchase volume crosses [N]".

---

## Anti-recommendations (do not suggest these)

- Doing a brand survey or customer interviews — out of scope for an analytics agent
- Building a custom analytics dashboard — already exists, that's what we're reading
- Switching from GA4 to another analytics tool — out of scope, expensive, slow
- Hiring more people / changing team structure — way out of scope
- Anything requiring more than 2 weeks of implementation work as a first move — at this stage, the inventory of cheap tests isn't yet exhausted
