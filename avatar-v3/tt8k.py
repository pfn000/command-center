
# 8K turntable of the run-9c Jena model, rendered from the SAVED 9c .blend exactly as built (no rebuild, no edits).
# Same studio as v37r9-turntable (the .blend carries the grey world, key/fill/rim suns, AgX Base Contrast, 85 mm camera),
# same relaxed pose rule as assemble.py@ed72771 pose_relaxed() with the 9c params, same framing rule (place(..., 'front', pad 1.04)).
import bpy, os, sys, math, time, json
from mathutils import Vector, Matrix
a=sys.argv[sys.argv.index('--')+1:]; BLEND,OUT=a[0],a[1]
E=os.environ; W_=int(E.get('TT_W','4320')); H_=int(E.get('TT_H','7680')); NF=int(E.get('TT_NF','300'))
SH=int(E.get('TT_SHARD','0')); SHN=int(E.get('TT_SHARDS','1')); SAMP=int(E.get('TT_SAMPLES','10'))
ONLY=[int(x) for x in E.get('TT_ONLY','').split(',') if x.strip()]
def log(*x): print('[tt8k]',*x,flush=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc=bpy.context.scene
arms=[o for o in sc.objects if o.type=='ARMATURE']
B=max(arms,key=lambda o:len([c for c in sc.objects if c.parent==o or any(m.type=='ARMATURE' and m.object==o for m in getattr(c,'modifiers',[]))]))
meshes=[o for o in sc.objects if o.type=='MESH' and not o.hide_render and o.visible_get()]
log('armature',B.name,'meshes',[o.name for o in meshes]); log('lights',[o.name for o in sc.objects if o.type=='LIGHT'],'camera',sc.camera.name if sc.camera else None)
log('engine',sc.render.engine,'view',sc.view_settings.view_transform,sc.view_settings.look,'exposure',sc.view_settings.exposure)
# 9c params (build-report.json of run 39172605668/A0)
P=dict(ARM_DOWN=45,SHOULDER_DOWN=10,ELBOW_BEND=-12,WRIST_BEND=8,RELAX=True)
def wrot(name,deg,axis):
    if not deg or name not in B.pose.bones: return
    pb=B.pose.bones[name]; h=pb.head.copy(); pb.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(deg),4,axis)@Matrix.Translation(-h)@pb.matrix; bpy.context.view_layer.update()
def pose_relaxed():
    # the saved file is in rest() state (= BANG bases), which is exactly where assemble.py's pose_relaxed() starts
    bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='POSE'); bpy.context.view_layer.update()
    SHD=P['SHOULDER_DOWN']
    for name,sgn,deg in (('Left shoulder',1,SHD),('Right shoulder',-1,SHD),('Left arm',1,P['ARM_DOWN']-SHD),('Right arm',-1,P['ARM_DOWN']-SHD)): wrot(name,sgn*deg,'Y')
    for sd,sgn in (('Left',1),('Right',-1)):
        wrot(sd+' elbow',P['ELBOW_BEND'],'X'); wrot(sd+' wrist',sgn*P['WRIST_BEND'],'Y')
        for f_ in ('IndexFinger','MiddleFinger','RingFinger','LittleFinger'):
            for j,a_ in ((1,18),(2,26),(3,18)): wrot(f'{f_}{j}_{sd[0]}',sgn*a_,'Y')
        for j in (1,2): wrot(f'Thumb{j}_{sd[0]}',sgn*14,'Y')
    if P['RELAX']:
        wrot('Right leg',-6,'X'); wrot('Right knee',14,'X')
        for nm_ in ('Right ankle','Right foot'):
            if nm_ in B.pose.bones: wrot(nm_,-6,'X'); break
    bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()
def bbox(objs):
    dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in objs:
        e=o.evaluated_get(dg); vv=e.data.vertices; st=max(1,len(vv)//4000); pts+=[e.matrix_world@vv[i].co for i in range(0,len(vv),st)]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); return mn,mx
cam=sc.camera
def place(res,pad,box):
    mn,mx=box; ce=(mn+mx)/2; sz=mx-mn; d_=Vector((0,-1,0)); asp=res[0]/res[1]
    wdt=abs(d_.y)*sz.x+abs(d_.x)*sz.y; need=max(sz.z,wdt/asp)*pad; dist=need/(24/85)+max(sz)/2
    sc.render.resolution_x,sc.render.resolution_y=res; sc.render.resolution_percentage=100; cam.data.lens=85; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24
    cam.location=ce+d_*dist; cam.rotation_euler=(ce-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.clip_start=dist*0.01; cam.data.clip_end=dist*4
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=SAMP; sc.cycles.use_denoising=True
try: sc.cycles.denoiser='OPENIMAGEDENOISE'
except Exception as e: log('denoiser',e)
sc.render.use_persistent_data=True; sc.render.film_transparent=False
sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=int(E.get('TT_Q','95'))
pose_relaxed()
mn,mx=bbox(meshes); R=0.5*max(mx.x-mn.x,mx.y-mn.y); cx_,cy_=(mn.x+mx.x)/2,(mn.y+mx.y)/2
box=(Vector((cx_-R,cy_-R,mn.z)),Vector((cx_+R,cy_+R,mx.z)))
place((W_,H_),1.04,box)
os.makedirs(OUT,exist_ok=True); M0=B.matrix_world.copy(); cc_=Vector((cx_,cy_,0))
per=(NF+SHN-1)//SHN; frames=ONLY or list(range(SH*per,min(NF,(SH+1)*per)))
log('res',W_,H_,'samples',SAMP,'frames',frames[0],'..',frames[-1])
for f in frames:
    t0=time.time()
    B.matrix_world=Matrix.Translation(cc_)@Matrix.Rotation(2*math.pi*f/NF,4,'Z')@Matrix.Translation(-cc_)@M0; bpy.context.view_layer.update()
    sc.render.filepath=OUT+f'/f{f:03d}.jpg'; bpy.ops.render.render(write_still=True); log('frame',f,round(time.time()-t0,1),'s')
log('DONE'); sys.stdout.flush(); os._exit(0)
