from PIL import Image, ImageDraw, ImageFont
F="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; R="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
W,H=1280,720
im=Image.new("RGB",(W,H)); d=ImageDraw.Draw(im)
for y in range(H):
    c=int(11+18*y/H); d.line([(0,y),(W,y)],fill=(c,c+3,c+10))
d.rectangle([0,0,W,12],fill=(118,185,0))
f=lambda s,p=F:ImageFont.truetype(p,s)
d.text((60,50),"DocBrief",font=f(54),fill=(118,185,0))
d.text((60,140),"Ask any 10-K.",font=f(112),fill=(255,255,255))
d.text((60,268),"Get the page.",font=f(112),fill=(118,185,0))
d.text((60,415),"Every answer cited. Every number checked.",font=f(36),fill=(200,208,220))
d.rounded_rectangle([60,490,1220,640],radius=18,fill=(24,30,42),outline=(118,185,0),width=4)
d.text((90,508),"Q  What is the revenue guidance for fiscal 2026?",font=f(28,R),fill=(160,170,185))
t="$560 – $580 million"; d.text((90,560),t,font=f(54),fill=(255,255,255))
x=90+d.textlength(t,font=f(54))+24
d.rounded_rectangle([x,566,x+90,616],radius=10,fill=(118,185,0)); d.text((x+18,573),"p.4",font=f(34),fill=(10,14,20))
d.text((60,665),"Bilingual: ask in English or Chinese",font=f(26,R),fill=(140,150,165))
s="NVIDIA Nemotron × Nebius"; w=d.textlength(s,font=f(28)); d.text((1220-w,660),s,font=f(28),fill=(118,185,0))
im.save("cover.png")
