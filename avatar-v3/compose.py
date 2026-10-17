
import sys,os
from PIL import Image, ImageDraw
IN,OUT=sys.argv[1],sys.argv[2]; P=OUT+'/proof'; BG=(51,51,51)
def onbg(p,size):
    im=Image.open(p).convert('RGBA'); bg=Image.new('RGBA',im.size,BG+(255,)); bg.alpha_composite(im); bg=bg.convert('RGB'); bg.thumbnail(size); return bg
pairs=[('front','front-full-1546.jpg'),('side','side-full.jpg'),('back','tall-864x1536.jpg')]
for name,ref in pairs:
    if not os.path.exists(P+'/'+name+'.png'): continue
    a=onbg(P+'/'+name+'.png',(700,1250)); r=Image.open(IN+'/refs/'+ref).convert('RGB'); r.thumbnail((700,1250))
    W=a.width+r.width+30; H=max(a.height,r.height)+40; c=Image.new('RGB',(W,H),BG); c.paste(r,(10,30)); c.paste(a,(r.width+20,30))
    d=ImageDraw.Draw(c); d.text((12,8),'her sheet: '+name,fill=(220,220,220)); d.text((r.width+22,8),'v3 build: '+name,fill=(220,220,220))
    c.save(P+'/cmp-'+name+'.jpg',quality=88); print('cmp',name)
for name in ('face','face34','front','side','back'):
    if os.path.exists(P+'/'+name+'.png'): onbg(P+'/'+name+'.png',(2000,2000)).save(P+'/'+name+'.jpg',quality=88)
