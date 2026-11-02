import { chromium } from 'playwright';
import assert from 'node:assert/strict';
const browser = await chromium.launch({headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
 for (const disabled of [true,false]) {
  const page = await browser.newPage({viewport:{width:1280,height:1000}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  if(disabled) await page.addInitScript(()=>{
   const original=HTMLCanvasElement.prototype.getContext;
   HTMLCanvasElement.prototype.getContext=function(type,...args){return /webgl/i.test(type)?null:original.call(this,type,...args);};
  });
  await page.goto(process.env.CARDIOLENS_TEST_URL || 'http://localhost:5173/cardiolens-3d-risk/');
  await page.locator(disabled?'.heart-scene[data-view="fallback"]':'.heart-webgl[data-webgl="ready"]').waitFor();
  if(disabled) assert.equal(await page.getByRole('heading',{name:'2D coronary map'}).count(),1);
  const badge = page.locator('.scene-vessel-badges button');
  assert.equal(await badge.count(),3);
  assert.match(await badge.nth(0).innerText(),/LAD.*\n?\d\.\d{2} \/ 1/s);
  await badge.nth(1).focus();await page.keyboard.press('Enter');
  assert.equal(await badge.nth(1).getAttribute('aria-pressed'),'true');
  await badge.nth(2).focus();await page.keyboard.press('Space');
  assert.equal(await badge.nth(2).getAttribute('aria-pressed'),'true');
  const before=await page.locator('.legend-gradient').evaluate(el=>el.style.background);
  await page.getByLabel('Vessel palette').selectOption('classic');
  const after=await page.locator('.legend-gradient').evaluate(el=>el.style.background);
  assert.notEqual(before,after);
  assert.equal(await badge.nth(2).getAttribute('aria-pressed'),'true');
  if (!disabled) {
   await page.locator('.heart-webgl canvas').evaluate(el=>el.dispatchEvent(new Event('webglcontextlost',{cancelable:true})));
   await page.locator('.heart-scene[data-view="fallback"]').waitFor();
   assert.equal(await page.locator('.heart-scene canvas').count(),0);
   await badge.nth(0).click();assert.equal(await badge.nth(0).getAttribute('aria-pressed'),'true');
  }
  await page.setViewportSize({width:375,height:812});
  await badge.nth(1).click();assert.equal(await badge.nth(1).getAttribute('aria-pressed'),'true');
  assert.deepEqual(errors,[]);
  console.log(disabled?'PASS: WebGL disabled → SVG, numeric labels, keyboard, palette, mobile selection; no page errors':'PASS: software WebGL → context loss cleanup → SVG; keyboard, palette, mobile selection; no page errors');
  await page.close();
 }
} finally {await browser.close();}
