const fs=require('node:fs'), vm=require('node:vm');
const assert=require('node:assert/strict'), path=require('node:path');
const html=fs.readFileSync('index.html','utf8');
const css=fs.readFileSync('luxury.css','utf8');
const menu=JSON.parse(fs.readFileSync('menu.json','utf8'));
assert(html.includes('href="luxury.css?v=20261116"'),'Luxury CSS not referenced');
assert(html.includes('class="hero luxe-hero"'),'New luxury hero missing');
assert(html.includes('class="luxe-photo-wall"'),'Real food photos not displayed');
assert(html.includes('function dishHTML'),'Lost menu cards');
assert(html.includes('function adminHTML'),'Lost admin dashboard');
assert(html.includes('function sendWhatsApp'),'Lost WhatsApp ordering');
assert(html.includes('function loadRepoMenu'),'Lost menu.json integration');
assert(html.includes('function refresh()'),'Lost photo gallery');
assert(html.includes("return chips;"),'Old duplicated carousel chips not removed');
assert(css.includes('.dish-img img{width:100%;height:100%;object-fit:contain!important'),'Gallery crop fix missing');
assert(css.includes('@media (max-width:720px)'),'Mobile layout missing');
const tags=[...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)];
assert(tags.length>=3,'Scripts missing');
tags.forEach((m,i)=>{
  if(/application\/ld\+json/.test(m[1])){JSON.parse(m[2]);return}
  new vm.Script(m[2],{filename:'index-script-'+i+'.js'});
});
const visible=Object.entries(menu.items).filter(([name,v])=>!v.hidden);
assert(visible.length>=35,'Visible food catalog unexpectedly small');
const missing=visible.filter(([name])=>!fs.existsSync(name));
assert.equal(missing.length,0,'Missing menu pictures: '+missing.map(([n])=>n).join('; '));
for(const media of [
 'WhatsApp Image 2026-08-28 at 12.17.51 (2).jpeg',
 'WhatsApp Image 2026-08-28 at 12.17.49.jpeg',
 'WhatsApp Image 2026-08-28 at 12.17.48 (3).jpeg',
 'chef.jpg'
])assert(fs.existsSync(media),'Hero/chef photo missing: '+media);
const cleaned = Object.entries(menu.items).filter(([,item])=>Boolean(item.cleaned_image));
// Cleaned images are optional: a dish must always remain on its original photographed table.
// A full-photo edit is permitted only after visual QA and source geometry checks.
for (const [name,item] of cleaned){
  assert(/^social\/cleaned\/[a-zA-Z0-9._-]+\.(?:jpe?g|png|webp)$/i.test(item.cleaned_image),
    'Invalid cleaned image path for '+name);
  assert(fs.existsSync(item.cleaned_image), 'Cleaned menu file missing: '+item.cleaned_image);
}
assert(html.includes('id="photos-switch"'),'Original/cleaned picture toggle missing');
assert(html.includes('S.showCleaned') && html.includes('f.originalUrl'),'Gallery is not reversible');
assert(html.includes('const priceText = f =>'),'Quote-only items must not display 0 MAD');
assert(html.includes('const cartTotalText = () =>'),'Unpriced items need an honest cart total');
assert(html.includes('itemOf(f).sale === true && iprice(f)>0 && iold(f)>iprice(f)'),'Sale badge must require a genuine discount');
assert(!html.includes('itemOf(f).sale !== false'),'Old default-on sale badge remains');
assert(!fs.readFileSync('fb-posts.html','utf8').includes('it.sale !== false'),
  'Facebook promo still treats nonexistent discounts as real');
new vm.Script(fs.readFileSync('tools/chefahmed/build_share_pages.js','utf8'),
  {filename:'build_share_pages.js'});
console.log('PASS — JS syntax:',tags.length,'HTML scripts; dishes:',visible.length,
  '— verified clean copies:',cleaned.length,'— accurate price/discount handling and static share generation.');
