// こよみ先生の6表情を assets/character/expressions.html（正式な描画元）から透明背景のPNGにする。
// まばたき用に、ふつう・かんがえ中の目だけを閉じた版も作る（ほかは元のSVGのまま）。
// 使い方: NODE_PATH=$(npm root -g) node scripts/render_expressions.js <出力フォルダ> [大きさpx]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [out, size = '480'] = process.argv.slice(2);
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1200, height: 800 } });
  await pg.goto('file://' + path.resolve(__dirname, '../assets/character/expressions.html'));
  const keys = await pg.evaluate(() => {
    // まばたき：目を細い線にする（元の closed() はにっこり用の弧なので使わない）
    const shut = (x, y) => `<path d="M${x - 11} ${y} h22" fill="none" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>`;
    FACES.normal_blink = { ...FACES.normal, eyes: shut(96, 112) + shut(144, 112) };
    FACES.think_blink = { ...FACES.think, eyes: shut(100, 104) + shut(152, 104) };
    return Object.keys(FACES);
  });
  for (const k of keys) {
    await pg.setContent(`<html><body style="margin:0;background:transparent"><div style="width:${size}px;height:${size}px">` +
      (await pg.evaluate(k => fuku(k), k)).replace('<svg ', `<svg width="${size}" height="${size}" style="overflow:visible" `) +
      '</div></body></html>');
    await pg.locator('div').screenshot({ path: path.join(out, `koyomi_${k}.png`), omitBackground: true });
  }
  await b.close();
})();
