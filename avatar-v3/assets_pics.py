
import sys,os,json,glob
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS=None
IN,OUT=sys.argv[1],sys.argv[2]; S=OUT+'/assets'; D=OUT+'/assets-preview'; os.makedirs(D,exist_ok=True)
try: FT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22); FS=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
except Exception: FT=FS=ImageFont.load_default()
BG=(46,46,46)
def burn(im,text):
    im=im.convert('RGB'); bar=44; c=Image.new('RGB',(im.width,im.height+bar),BG); c.paste(im,(0,0)); d=ImageDraw.Draw(c)
    d.text((12,im.height+10),text[:150],fill=(235,235,235),font=FT); return c
def checker(sz,n=16):
    c=Image.new('RGB',sz,(120,120,120)); d=ImageDraw.Draw(c); s=max(8,sz[0]//n)
    for y in range(0,sz[1],s):
        for x in range(0,sz[0],s):
            if (x//s+y//s)%2: d.rectangle([x,y,x+s-1,y+s-1],fill=(150,150,150))
    return c
def tile(p,t=420):
    im=Image.open(p); im.thumbnail((t,t)); 
    if im.mode in ('RGBA','LA','P'):
        im=im.convert('RGBA'); c=checker(im.size); c.paste(im,(0,0),im); im=c
    else: im=im.convert('RGB')
    cell=Image.new('RGB',(t,t+40),BG); cell.paste(im,((t-im.width)//2,(t-im.height)//2)); d=ImageDraw.Draw(cell)
    try: sz=Image.open(p).size
    except Exception: sz=('?','?')
    d.text((6,t+4),os.path.basename(p)[:44],fill=(230,230,230),font=FS); d.text((6,t+21),f'{sz[0]}x{sz[1]}',fill=(170,170,170),font=FS); return cell
def sheet(paths,name,label,cols=4):
    paths=[p for p in paths if os.path.exists(p)]
    if not paths: print('no textures for',name); return None
    ts=[tile(p) for p in paths]; cols=min(cols,len(ts)); rows=(len(ts)+cols-1)//cols; w,h=ts[0].size
    c=Image.new('RGB',(cols*w+(cols+1)*10,rows*h+(rows+1)*10),BG)
    for i,t in enumerate(ts): c.paste(t,(10+(i%cols)*(w+10),10+(i//cols)*(h+10)))
    c=burn(c,label); fn=f'{name}-picture.jpg'; c.save(D+'/'+fn,quality=84); print('picture',fn,len(paths)); return fn
PF=IN+"/Panda's Fit Base (High - Flat Foot)/"; HT=IN+'/1691108855vrmodels_store_female-head-by-bunisu/Female head/female head textures/'; ZP=IN+'/ZinPia_Doe Eyes (Sunny Head)/'
G={
 'panda-body':([PF+f for f in ('BODY.png','BODY (No Nail on Body).png','Body UV.png','JUST THE  BASE.png','Skin 1.png')],"Panda's Fit Base (High - Flat Foot) textures"),
 'female-head':([HT+f'{i}.png' for i in range(1,6)]+[IN+'/assets/face_skin_2_from_saidie_1708.jpg'],'Female head textures 1-5.png (bunisu) + face_skin_2_from_saidie_1708.jpg'),
 'skin-texture-set':([PF+'BODY.png',PF+'BODY (No Nail on Body).png',PF+'Skin 1.png']+[HT+f'{i}.png' for i in range(1,6)]+[IN+'/assets/face_skin_2_from_saidie_1708.jpg'],'Every skin map in her upload: Panda BODY / BODY no nail / Skin 1 (matcap) + head pack 1-5 + face_skin_2'),
 'zinpia-eyes':(sorted(glob.glob(ZP+'*.png')),'ZinPia_Doe_Eyes_Sunny_Head.zip (all eye textures)'),
 'blowout-haircards':([IN+'/Textures/B&W.png',IN+'/Textures/B.png',IN+'/Textures/W.png',IN+'/assets/hair_texture_black_to_white_1713.jpg'],"Blowout hair textures (Textures/B&W, B, W) + hair_texture_black_to_white_1713.jpg"),
 'booty-shorts':(sorted(glob.glob(IN+'/Textures/Colors/*.png'))+sorted(glob.glob(IN+'/Textures/Main/*.png')),'Booty Shorts by Beanie textures (Textures/Colors + Textures/Main)'),
 'outfit-shirt':(sorted(glob.glob(IN+'/Tshirt-*.png')),'Outfitriggedpanda shirt textures (Tshirt-*.png)'),
 'promo':([IN+'/Promo Cover.png',IN+'/Promo mesh + bones.png'],'Promo Cover.png + Promo mesh + bones.png'),
 'her-photos':(sorted(glob.glob(IN+'/assets/*-*-*-*.jpg')),'assets/*.jpg (her uploaded photos/refs)'),
}
PICS={}
for k,(ps,l) in G.items(): PICS[k]=sheet(ps,k,l,cols=5 if len(ps)>8 else 4)
man=json.load(open(S+'/manifest.json')) if os.path.exists(S+'/manifest.json') else {'renders':[],'info':{}}
REN={}
for r in man['renders']:
    p=S+'/'+r['file']
    if not os.path.exists(p): continue
    fn=r['file'].replace('.png','.jpg'); burn(Image.open(p),r['label']).save(D+'/'+fn,quality=86); REN.setdefault(r['asset'],[]).append(fn); print('render',fn)
json.dump({'pictures':PICS,'renders':REN,'info':man.get('info',{}),'all_files':sorted(os.path.relpath(os.path.join(r,f),IN) for r,ds,fs in os.walk(IN) if '.cache' not in r for f in fs)},open(D+'/index.json','w'),indent=1)
