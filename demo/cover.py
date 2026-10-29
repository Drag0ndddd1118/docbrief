from PIL import Image, ImageDraw, ImageFont
F="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; R="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
W,H=1280,720; G=(118,185,0)
im=Image.new("RGB",(W,H)); d=ImageDraw.Draw(im)
for y in range(H):
    c=int(11+18*y/H); d.line([(0,y),(W,y)],fill=(c,c+3,c+10))
d.rectangle([0,0,W,12],fill=G)
f=lambda s,p=F:ImageFont.truetype(p,s)
d.text((60,44),"DocBrief",font=f(46),fill=G)
d.text((60,110),"Ask any 10-K.",font=f(108),fill=(255,255,255))
d.text((60,232),"Get the page.",font=f(108),fill=G)
d.text((60,372),"AI that cites every answer, verifies every number,",font=f(34),fill=(214,220,230))
d.text((60,418),"and fact-checks the claims against the live web.",font=f(34),fill=(214,220,230))
# answer card
d.rounded_rectangle([60,486,850,640],radius=18,fill=(24,30,42),outline=G,width=4)
d.text((88,502),"Q  Who are NVIDIA's biggest customers?",font=f(26,R),fill=(160,170,185))
t="22% + 14% of revenue"; d.text((88,548),t,font=f(46),fill=(255,255,255))
x=88+d.textlength(t,font=f(46))+20
d.rounded_rectangle([x,554,x+84,602],radius=10,fill=G); d.text((x+14,560),"p.7",font=f(32),fill=(10,14,20))
d.text((88,606),"real NVIDIA FY2026 10-K  ·  cited to the page",font=f(20,R),fill=(140,150,165))
# fact-check badge
d.rounded_rectangle([880,486,1220,640],radius=18,fill=(18,34,26),outline=(58,170,110),width=3)
d.text((894,504),"✓",font=f(1,R),fill=G) if False else None
d.text((904,506),"Fact-checked by Tavily",font=f(22),fill=(255,255,255))
d.text((904,550),"PDF claim  vs  live web",font=f(22,R),fill=(190,200,210))
d.rounded_rectangle([904,590,1100,626],radius=10,fill=(30,80,55)); d.text((920,596),"consistent",font=f(22),fill=(150,235,180))
d.text((60,668),"Nemotron Nano · Super · Ultra  ×  Nebius Token Factory  ×  Tavily",font=f(25),fill=G)
im.save("cover.png")
