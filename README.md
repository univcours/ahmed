# الشيف أحمد — Chef Ahmed Catering

موقع معرض الأطباق المغربية للشيف أحمد بسطات. يعمل كصفحة ثابتة على GitHub Pages، مع تصفح عربي/إنجليزي، معرض، بحث وتصنيفات، سلة إرسال الطلب عبر واتساب، وصفحات معاينة للمشاركة.

**Live site:** https://univcours.github.io/ahmed/

## How the website works

- `index.html` — Arabic/English UI, menu, gallery, cart and WhatsApp enquiries.
- `luxury.css` — responsive presentation, including the cleaned/original photo switch.
- `menu.json` — the **only source** of catalog items, names, captions, prices and display-image references.
- Original food photos — root-level `WhatsApp Image*.jpeg` files. **Do not overwrite or delete them.**
- `social/cleaned/` — optional images with digitally cleaned surfaces. The corresponding original remains available and is the fallback on image errors.
- `share/` — historical sharing pages; **public deployment regenerates fresh share metadata from `menu.json`** using `tools/chefahmed/build_share_pages.js`.
- `fb-posts.html` — optional Facebook post text/photo preparation tool.
- `.github/workflows/static.yml` — the sole Pages publishing pipeline.
- `tools/chefahmed/site_qa.js` — automated integrity checks.

## Price integrity

If an item's `price` is `0` or missing, the site says **الثمن عند الطلب / Price on request**. It never claims that the item costs zero dirhams. WhatsApp orders request a price confirmation for unpriced products; totals are displayed only when every item has a price.

A **SALE** label only appears when `sale: true` and `old_price > price > 0`. Do not set a sale badge without a genuine previous selling price. The Facebook draft page uses the same pricing logic.

## Photo cleanup without losing originals

For an item in `menu.json`, use a safe optional attribute:

```json
{
  "name_ar": "بسطيلة بالقمرون",
  "price": 0,
  "cleaned_image": "social/cleaned/food-07.jpg"
}
```

The website defaults to showing cleaned surroundings where an edited asset exists and offers an accessible button to display the **original** for comparison. If a cleaned file is missing or fails to load, it falls back to the real original photo automatically. Never present AI-recreated dishes as original photography; carefully inspect cutout edges and garnishes before enabling a retouched copy.

## Build, testing and deployment

Run with Node.js 22 or newer:

```bash
node tools/chefahmed/site_qa.js
node tools/chefahmed/build_share_pages.js _public/share
```

Pushing to `main` automatically validates and deploys the visitor-facing assets through `.github/workflows/static.yml`. A second Jekyll deploy workflow was retired to avoid conflicting GitHub Pages publications.

The public Pages artifact includes the site, original photos, reviewed cleaned photos, menu, media and sharing pages; it excludes CI scripts, workflow files and `token.enc`. **Note:** excluding a file from the Pages artifact does **not** make it private when it is tracked in a public GitHub repository.

## Security caution — important

This static project contains a browser-based manager and a historic encrypted GitHub credential workflow. A client-side PIN or encrypted `token.enc` in a **public** repository is **not equivalent to secure, server-side authentication**. Weak PINs can be attacked offline, and local browser storage of an access token is risky.

For a production admin dashboard, revoke and replace any exposed GitHub token, remove token storage from the public repository's Git history through an approved migration, and use a server-side authenticated integration with narrowly scoped privileges (GitHub App/OAuth backend, or GitHub Actions workflow with protected secrets). Do not put Personal Access Tokens or Facebook Page Access Tokens into HTML, `menu.json`, or commits. The existing admin write flow is legacy functionality, **not a security boundary**.

## Public-site quality gates

The CI checks that the catalog is present, photographs have local originals, each selected cleaned image exists, inline JavaScript parses, the reversible photo switch exists, and unpriced products and non-existent discounts are not advertised falsely. New photos should be visually reviewed on desktop and mobile before release.
