import json, sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageStat
F='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
EP='/home/claude/koyomi-company/outputs/2026-11-23_012'; Q=1
def neutral(im, target=1.45):
    r,g,b=ImageStat.Stat(im.resize((100,100))).mean
    ratio=r/max(b,1)
    if ratio<=target: return im
    k=(target/ratio)**0.5          # 赤を下げ、青を上げて半分ずつ寄せる
    R,G,B=im.split()
    R=R.point(lambda v:min(255,int(v*k))); B=B.point(lambda v:min(255,int(v/k)))
    return Image.merge('RGB',(R,G,B))
def pics(fix, sat):
    a=Image.open(f'{EP}/q{Q}_a.png').convert('RGB'); b=Image.open(f'{EP}/q{Q}_b.png').convert('RGB')
    ans=json.load(open(f'{EP}/answers.json',encoding='utf-8'))
    A=[x for x in ans['questions'] if x['q']==Q][0]; W,H=a.size
    bx=[x['box_px'] for x in A['answers']]
    x0=min(v[0] for v in bx);y0=min(v[1] for v in bx);x1=max(v[2] for v in bx);y1=max(v[3] for v in bx)
    top=170;ph=720-top;pw=636;r=pw/ph
    w=max(x1-x0,(y1-y0)*r)*1.3;h=w/r
    if w>W:w,h=W,W/r
    if h>H:h,w=H,H*r
    cx=min(max((x0+x1)/2,w/2),W-w/2);cy=min(max((y0+y1)/2+h*0.08,h/2),H-h/2)
    box=(int(cx-w/2),int(cy-h/2),int(cx+w/2),int(cy+h/2))
    def prep(im):
        if fix: im=neutral(im)
        im=im.crop(box).resize((pw,ph),Image.LANCZOS)
        im=ImageEnhance.Color(im).enhance(sat); im=ImageEnhance.Contrast(im).enhance(1.15 if fix else 1.3)
        return im.filter(ImageFilter.UnsharpMask(2,130,2))
    return prep(a),prep(b),top
def make(out, band, parts, fix=True, sat=1.15, bottom=('間違いさがし',)):
    pa,pb,top=pics(fix,sat)
    T=Image.new('RGB',(1280,720),(255,255,255)); T.paste(pa,(0,top)); T.paste(pb,(644,top))
    d=ImageDraw.Draw(T); d.rectangle([636,top,644,720],fill=(25,25,25)); d.rectangle([0,0,1280,top],fill=band)
    f=ImageFont.truetype(F,150)
    tw=sum(d.textlength(s,font=f) for s,_,_,_ in parts)
    if tw>1240: f=ImageFont.truetype(F,int(150*1240/tw)); tw=sum(d.textlength(s,font=f) for s,_,_,_ in parts)
    x=(1280-tw)/2
    for s,fill,sw,sc in parts:
        d.text((x,top/2+4),s,font=f,fill=fill,anchor='lm',stroke_width=sw,stroke_fill=sc); x+=d.textlength(s,font=f)
    g=Image.new('L',(1280,220),0);gd=ImageDraw.Draw(g)
    for i in range(220): gd.line([(0,i),(1280,i)],fill=int(170*i/220))
    T.paste(Image.new('RGB',(1280,220),(0,0,0)),(0,500),g)
    f2=ImageFont.truetype(F,158)
    bw=sum(d.textlength(s,font=f2) for s in bottom)
    if bw>1080: f2=ImageFont.truetype(F,int(158*1080/bw)); bw=sum(d.textlength(s,font=f2) for s in bottom)
    x=(1280-bw)/2-40 if bw>900 else (1280-bw)/2
    for i,s in enumerate(bottom):
        c=(255,214,0) if (len(bottom)>1 and i==0) else (255,255,255)
        d.text((x,618),s,font=f2,fill=c,anchor='lm',stroke_width=14,stroke_fill=(0,0,0)); x+=d.textlength(s,font=f2)
    T.save(out,quality=92)
K=(0,0,0);Wt=(255,255,255);Y=(255,214,0);R=(230,30,30)
O='/home/claude/work/thumbproto/'
make(O+'0_今の形（比較用）.jpg',K,[('60〜70代',(255,45,45),2,K),('の脳トレ',Wt,2,K)],fix=False,sat=1.5)
make(O+'A_黒帯・黄と白.jpg',K,[('60〜70代',Y,2,K),('の脳トレ',Wt,2,K)])
make(O+'B_黄色帯・黒文字・赤に白縁.jpg',Y,[('60〜70代',R,10,Wt),('の脳トレ',K,0,K)])
make(O+'C_白帯・黒文字・赤に黒縁.jpg',Wt,[('60〜70代',R,0,K),('の脳トレ',K,0,K)])
make(O+'D_黒帯・白文字・赤に白縁.jpg',K,[('60〜70代',R,9,Wt),('の脳トレ',Wt,2,K)])
make(O+'E_黄色帯・難問.jpg',Y,[('60〜70代',R,10,Wt),('の脳トレ',K,0,K)],bottom=('難問！','間違いさがし'))
