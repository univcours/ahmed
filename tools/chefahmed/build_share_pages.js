/**
 * Generate accurate social-sharing previews from menu.json.
 * Stale, hand-written share HTML can accidentally advertise a made-up price.
 * Run: node tools/chefahmed/build_share_pages.js _public/share
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');

const SITE = 'https://univcours.github.io/ahmed/';
const MENU = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'menu.json'), 'utf8'));
const outDir = process.argv[2] || '_public/share';
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
})[ch]);
const slug = name => {
  const readable = String(name).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'');
  if (readable && !/^(png|jpg|jpeg|webp|gif)$/.test(readable)) return readable;
  // Arabic-only photo filenames must not all collapse to 'png'.
  const bytes = new TextEncoder().encode(String(name));
  return 'photo-' + Array.from(bytes, b=>b.toString(16).padStart(2,'0')).join('');
};
const fileUrl = file => SITE + file.split('/').map(encodeURIComponent).join('/');

function render(name, item) {
  const clean = item.cleaned_image;
  const safeClean = typeof clean === 'string' &&
    /^social\/cleaned\/[a-zA-Z0-9._-]+\.(?:jpe?g|png|webp)$/i.test(clean);
  const picture = fileUrl(safeClean ? clean : name);
  const rawPrice = Number(item.price);
  const price = Number.isFinite(rawPrice) && rawPrice > 0 ? rawPrice + ' درهم' : 'الثمن عند الطلب';
  const title = (item.name_ar || 'طبق من مطبخ الشيف أحمد') + ' — ' + price + ' 🍽️ الشيف أحمد';
  const desc = (item.desc_ar || 'أطباق مغربية ومناسبات مع الشيف أحمد') +
    ' • للحجز والاستفسار: 0689199142';
  const source = SITE + 'share/' + slug(name) + '.html';
  const landing = SITE + '#menu-start';
  return [
    '<!DOCTYPE html>',
    '<html lang="ar" dir="rtl">',
    '<head>',
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    '<meta name="robots" content="noindex, follow">',
    '<title>' + escapeHtml(title) + '</title>',
    '<meta name="description" content="' + escapeHtml(desc) + '">',
    '<link rel="canonical" href="' + SITE + '">',
    '<meta property="og:type" content="website">',
    '<meta property="og:site_name" content="الشيف أحمد">',
    '<meta property="og:title" content="' + escapeHtml(title) + '">',
    '<meta property="og:description" content="' + escapeHtml(desc) + '">',
    '<meta property="og:image" content="' + escapeHtml(picture) + '">',
    '<meta property="og:url" content="' + escapeHtml(source) + '">',
    '<meta property="og:locale" content="ar_MA">',
    '<meta name="twitter:card" content="summary_large_image">',
    '<meta name="twitter:title" content="' + escapeHtml(title) + '">',
    '<meta name="twitter:description" content="' + escapeHtml(desc) + '">',
    '<meta name="twitter:image" content="' + escapeHtml(picture) + '">',
    '</head>',
    '<body style="margin:0;background:#F7F2E9;color:#173B34;font-family:system-ui;text-align:center">',
    '<main style="padding:30px">',
    '<h1>' + escapeHtml(item.name_ar || 'الشيف أحمد') + '</h1>',
    '<p>' + escapeHtml(price) + '</p>',
    '<p>جارٍ فتح قائمة الأطباق… <a href="' + landing + '">تصفح قائمة الشيف أحمد</a></p>',
    '</main>',
    '<script>location.replace(' + JSON.stringify(landing) + ');<\/script>',
    '</body>',
    '</html>',
    ''
  ].join('\n');
}

fs.mkdirSync(outDir, { recursive: true });
let count = 0;
const used = new Set();
for (const [name, item] of Object.entries(MENU.items || {})) {
  if (item.hidden) continue;
  const nameSlug = slug(name);
  if (!nameSlug || used.has(nameSlug)) throw new Error('Duplicate or invalid share slug: ' + name);
  used.add(nameSlug);
  fs.writeFileSync(path.join(outDir, nameSlug + '.html'), render(name, item), 'utf8');
  count++;
}
if (!count) throw new Error('The public catalog is empty');
console.log('Created', count, 'share previews with accurate menu prices in', outDir);
