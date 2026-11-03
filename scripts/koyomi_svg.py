"""こよみ先生（茶色のふくろう）をSVGで描く。色は knowledge/character.md に合わせる。
表情は今は「ふつう」（出題）だけ。ほかの5種類は今後追加する。"""
C = dict(body="#b08a5f", belly="#f3e3c3", beak="#f0a830", line="#3b2f25", cheek="#f2a0a0")


def koyomi_svg(expression="futsu", size=400):
    if expression != "futsu":
        raise NotImplementedError(expression)
    c, lw = C, 4
    eyes = "".join(f'''
  <circle cx="{x}" cy="150" r="46" fill="#fffaf0" stroke="{c['line']}" stroke-width="{lw}"/>
  <circle cx="{x}" cy="150" r="34" fill="none" stroke="{c['line']}" stroke-width="{lw}"/>
  <circle cx="{x+4}" cy="154" r="15" fill="{c['line']}"/>
  <circle cx="{x+9}" cy="148" r="5" fill="#fff"/>''' for x in (150, 250))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="{size}" height="{size}">
 <g stroke-linejoin="round" stroke-linecap="round">
  <path d="M118 78 L104 26 L160 62 Z M282 78 L296 26 L240 62 Z" fill="{c['body']}" stroke="{c['line']}" stroke-width="{lw}"/>
  <ellipse cx="200" cy="215" rx="140" ry="160" fill="{c['body']}" stroke="{c['line']}" stroke-width="{lw}"/>
  <path d="M68 220 Q40 290 96 340 Q104 280 92 230 Z M332 220 Q360 290 304 340 Q296 280 308 230 Z" fill="{c['body']}" stroke="{c['line']}" stroke-width="{lw}"/>
  <ellipse cx="200" cy="275" rx="88" ry="92" fill="{c['belly']}" stroke="{c['line']}" stroke-width="{lw}"/>
  {eyes}
  <ellipse cx="112" cy="212" rx="20" ry="12" fill="{c['cheek']}" opacity="0.7"/>
  <ellipse cx="288" cy="212" rx="20" ry="12" fill="{c['cheek']}" opacity="0.7"/>
  <path d="M186 186 L214 186 L200 214 Z" fill="{c['beak']}" stroke="{c['line']}" stroke-width="{lw}"/>
  <path d="M160 372 v16 M176 374 v14 M224 374 v14 M240 372 v16" stroke="{c['beak']}" stroke-width="8"/>
 </g>
</svg>'''


def render_png(svg, out_path, size=400):
    """Node版Playwright（Chromium）で透明背景のPNGにする。"""
    import json, subprocess, tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as f:
        f.write(svg)
    js = """const {chromium}=require('playwright');const fs=require('fs');(async()=>{
const [svgPath,out,size]=process.argv.slice(1);const b=await chromium.launch();
const pg=await b.newPage({viewport:{width:+size,height:+size}});
await pg.setContent('<html><body style="margin:0;background:transparent">'+fs.readFileSync(svgPath,'utf8')+'</body></html>');
await pg.locator('svg').screenshot({path:out,omitBackground:true});await b.close();})();"""
    subprocess.run(["node", "-e", js, f.name, out_path, str(size)], check=True)
