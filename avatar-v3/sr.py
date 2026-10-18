# v3.3: learned super-resolution for the Meshy face area of its texture (CPU). args: dir factor model mix
import sys, json, numpy as np, time
from PIL import Image, ImageDraw, ImageFilter
d=sys.argv[1]; F=float(sys.argv[2]); MODEL=sys.argv[3]; MIX=float(sys.argv[4]) if len(sys.argv)>4 else 1.0
t0=time.time()
crop=np.load(d+'/crop.npy'); tris=np.load(d+'/tris.npy'); h,w=crop.shape[:2]
mask=Image.new('L',(w,h),0); dr=ImageDraw.Draw(mask)
for t in tris: dr.polygon([(float(p[0]),float(p[1])) for p in t],fill=255)
mask=mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(5))
m=np.asarray(mask).astype(np.float32)/255.0
rgb=(np.clip(crop[:,:,:3],0,1)*255+0.5).astype(np.uint8)
import torch
torch.set_num_threads(max(1,__import__('os').cpu_count()))
from spandrel import ModelLoader
desc=ModelLoader().load_from_file(MODEL); desc.eval(); S=desc.scale
print('model',type(desc.model).__name__,'scale',S,'crop',w,h,'mask px',int((m>0).sum()),flush=True)
out=rgb.astype(np.float32)/255.0; T=int(sys.argv[5]) if len(sys.argv)>5 else 320; PAD=24; done=0
for y in range(0,h,T):
    for x in range(0,w,T):
        if m[y:y+T,x:x+T].max()<=0: continue
        ya,xa=max(0,y-PAD),max(0,x-PAD); yb,xb=min(h,y+T+PAD),min(w,x+T+PAD)
        tile=Image.fromarray(rgb[ya:yb,xa:xb]); tw,th=tile.size
        small=tile.resize((max(8,int(round(tw/F))),max(8,int(round(th/F)))),Image.LANCZOS)
        xt=torch.from_numpy(np.asarray(small).astype(np.float32)/255.0).permute(2,0,1)[None]
        with torch.no_grad(): yt=desc(xt)
        up=Image.fromarray((yt[0].permute(1,2,0).clamp(0,1).numpy()*255+0.5).astype(np.uint8)).resize((tw,th),Image.LANCZOS)
        ua=np.asarray(up).astype(np.float32)/255.0
        out[y:min(h,y+T),x:min(w,x+T)]=ua[y-ya:y-ya+min(T,h-y),x-xa:x-xa+min(T,w-x)]; done+=1
res=np.zeros((h,w,5),dtype=np.float32); res[:,:,:3]=out; res[:,:,3]=crop[:,:,3] if crop.shape[2]>3 else 1; res[:,:,4]=m*MIX
np.save(d+'/out.npy',res)
# before/after previews (flipped to image orientation: Blender rows start at the bottom)
Image.fromarray(rgb[::-1]).save(d+'/before.png'); Image.fromarray((np.clip(rgb.astype(np.float32)/255*(1-m[...,None]*MIX)+out*m[...,None]*MIX,0,1)*255).astype(np.uint8)[::-1]).save(d+'/after.png')
print('SR done tiles',done,'secs',round(time.time()-t0,1),flush=True)
