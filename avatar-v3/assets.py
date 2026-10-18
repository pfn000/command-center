
# v3.7 STEP 1: render each of Saidie's uploaded assets ALONE, neutral grey, 3-point light, her own textures (no Meshy, no build edits)
import bpy, sys, os, math, json
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]; IN,OUT=argv[0],argv[1]; O=OUT+'/assets'; os.makedirs(O,exist_ok=True)
import time as _t; _T0=_t.time()
def log(*a): print('[v3]',f'{_t.time()-_T0:.0f}s',*a,flush=True)
FILES={}
for r,ds,fs in os.walk(IN):
    if '/.cache' in r: continue
    for f in fs: FILES.setdefault(f.lower(),os.path.join(r,f))
log('files indexed',len(FILES))
MAN=[]; SAMPLES=int(os.environ.get('AS_SAMPLES','24'))
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=SAMPLES; sc.cycles.use_denoising=True
    sc.render.film_transparent=False; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGB'
    sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Base Contrast'
    w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.18,0.18,0.18,1); bg.inputs[1].default_value=1.0
    def sun(name,rot,e,col=(1,1,1)):
        L=bpy.data.lights.new(name,'SUN'); L.energy=e; L.color=col; L.angle=math.radians(8); o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.rotation_euler=[math.radians(a) for a in rot]
    sun('key',(55,0,-35),3.2,(1,0.96,0.92)); sun('fill',(70,0,45),1.1,(0.92,0.95,1)); sun('rim',(60,0,165),2.4)
    return sc
def fix_images():
    miss=[]
    for im in bpy.data.images:
        if im.source!='FILE': continue
        p=bpy.path.abspath(im.filepath)
        if im.packed_file or (p and os.path.exists(p) and im.size[0]>0): continue
        b=os.path.basename(p.replace('\\','/')).lower()
        if b in FILES: im.filepath=FILES[b]; im.reload(); log('relinked',im.name,'->',FILES[b][len(IN):])
        else: miss.append(im.name)
    return miss
def set_tex(mat,path,alpha=False):
    if not path or not os.path.exists(path): return False
    mat.use_nodes=True; nt=mat.node_tree; b=[n for n in nt.nodes if n.type=='BSDF_PRINCIPLED']
    if not b: b=[nt.nodes.new('ShaderNodeBsdfPrincipled')]; nt.links.new(b[0].outputs[0],[n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'][0].inputs[0])
    b=b[0]; t=nt.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(path,check_existing=True)
    nt.links.new(t.outputs[0],b.inputs['Base Color'])
    if alpha: nt.links.new(t.outputs[1],b.inputs['Alpha'])
    return True
def mats_report(objs):
    out=[]
    for o in objs:
        if o.type!='MESH': continue
        for s in o.material_slots:
            m=s.material
            if not m: continue
            ims=[n.image.name for n in m.node_tree.nodes if m.use_nodes and n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []
            out.append({'object':o.name,'material':m.name,'textures':ims})
    return out
def frame_and_render(sc,objs,name,label,views=('front','q34','back'),res=(900,1200)):
    dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in objs:
        if o.type!='MESH': continue
        e=o.evaluated_get(dg); vv=e.data.vertices; st=max(1,len(vv)//4000)
        pts+=[e.matrix_world@vv[i].co for i in range(0,len(vv),st)]
    if not pts: log('no geometry',name); return
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); ce=(mn+mx)/2; sz=mx-mn
    cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=85
    sc.render.resolution_x,sc.render.resolution_y=res
    dirs={'front':Vector((0,-1,0)),'back':Vector((0,1,0)),'side':Vector((-1,0,0)),'q34':Vector((-0.72,-0.69,0)).normalized()}
    asp=res[0]/res[1]
    for v in views:
        d_=dirs[v]; wdt=abs(d_.y)*sz.x+abs(d_.x)*sz.y; hgt=sz.z
        cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24
        need=max(hgt, wdt/asp)*1.12; dist=need/(24/85)+max(sz)/2
        cam.location=ce+d_*dist; cam.rotation_euler=(ce-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.clip_start=dist*0.01; cam.data.clip_end=dist*4
        fn=f'{name}-render-{v}.png'; sc.render.filepath=O+'/'+fn; bpy.ops.render.render(write_still=True); log('render',fn)
        MAN.append({'asset':name,'file':fn,'label':f'{label}  ({v})','kind':'render'})
    bpy.data.objects.remove(cam)
def imp_fbx(path):
    before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=path); return [o for o in bpy.data.objects if o not in before]
INFO={}
def job(name,label,fn):
    try:
        sc=reset(); objs,tex=fn(sc); miss=fix_images()
        INFO[name]={'label':label,'objects':[(o.name,o.type,sum(len(p.vertices)-2 for p in o.data.polygons) if o.type=='MESH' else None) for o in objs],'materials':mats_report(objs),'missing_images':miss,'textures':tex}
        log('asset',name,INFO[name])
        frame_and_render(sc,[o for o in objs if o.visible_get()],name,label)
    except Exception as e:
        import traceback; traceback.print_exc(); INFO[name]={'label':label,'error':str(e)}; log('ASSETERR',name,e)
    json.dump({'renders':MAN,'info':INFO},open(O+'/manifest.json','w'),indent=1,default=str)
F=lambda n: FILES.get(n.lower())
BF=IN+"/Panda's Fit Base (High - Flat Foot)/"
# 1 Panda body (.blend, appended as the pack says)
def a_body(sc):
    with bpy.data.libraries.load(BF+"Panda's Fit Base (High - Flat Foot).blend",link=False) as (df,dt): dt.objects=list(df.objects)
    objs=[]
    for o in dt.objects:
        if o is None: continue
        sc.collection.objects.link(o); objs.append(o)
    for im_ in bpy.data.images:
        base=im_.name.split('.png')[0]+'.png'
        if os.path.exists(BF+base): im_.filepath=BF+base; im_.reload()
    return objs,["Panda's Fit Base/BODY.png","Panda's Fit Base/Skin 1.png (matcap)"]
job('panda-body',"Panda's Fit Base (High - Flat Foot).blend  [Body + Armature, her authored BODY.png / Skin 1.png]",a_body)
# 2 Female Head + hair (bunisu) as shipped, with her face skin 1.png + ZinPia doe 5 eyes
HD=IN+'/1691108855vrmodels_store_female-head-by-bunisu/Female head/'
ZP=IN+'/ZinPia_Doe Eyes (Sunny Head)/'
def head_mats(objs,face='1.png'):
    for o in objs:
        if o.type!='MESH': continue
        for s in o.material_slots:
            m=s.material
            if not m: continue
            n=m.name.lower()
            if n.startswith('face'): set_tex(m,HD+'female head textures/'+face,alpha=True); m.blend_method='HASHED' if hasattr(m,'blend_method') else None
            elif n.startswith('eyes'): set_tex(m,ZP+'doe 5.png')
            elif n.startswith('effects'):
                m.use_nodes=True; b=[x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED']
                if b: b[0].inputs['Alpha'].default_value=0.0
def a_headhair(sc):
    objs=imp_fbx(HD+'Female head + hair.fbx'); head_mats(objs)
    return objs,['female head textures/1.png','ZinPia doe 5.png']
job('female-head-plus-hair',"Female head + hair.fbx (bunisu) as shipped  [face: female head textures/1.png, eyes: ZinPia doe 5]",a_headhair)
def a_head(sc):
    objs=imp_fbx(HD+'Female head + hair.fbx')
    for o in list(objs):
        if o.type=='MESH' and o.name!='Female Head': bpy.data.objects.remove(o); objs.remove(o)
    head_mats(objs); return objs,['female head textures/1.png','ZinPia doe 5.png']
job('female-head',"Female Head mesh alone (from Female head + hair.fbx)  [face 1.png, eyes ZinPia doe 5]",a_head)
def a_eyes(sc):
    objs=imp_fbx(HD+'Female head + hair.fbx'); keep=[]
    for o in list(objs):
        if o.type=='MESH' and o.name!='Female Head': bpy.data.objects.remove(o); objs.remove(o)
    head_mats(objs); return objs,['ZinPia doe 5.png']
# eyes close-up: same head, camera on the eye band
def eyes_job():
    try:
        sc=reset(); objs,tex=a_eyes(sc); fix_images()
        fh=[o for o in objs if o.type=='MESH'][0]; me=fh.data; mi={i:(s.material.name.lower() if s.material else '') for i,s in enumerate(fh.material_slots)}
        pts=[fh.matrix_world@p.center for p in me.polygons if mi[p.material_index].startswith('eyes')]
        mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); ce=(mn+mx)/2; sz=mx-mn
        cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=85; cam.data.sensor_fit='HORIZONTAL'; cam.data.sensor_width=36
        sc.render.resolution_x,sc.render.resolution_y=1200,600; dist=sz.x*1.5/(36/85)
        cam.location=ce+Vector((0,-1,0))*dist; cam.rotation_euler=(ce-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.clip_start=dist*0.01; cam.data.clip_end=dist*4
        sc.render.filepath=O+'/zinpia-eyes-render-front.png'; bpy.ops.render.render(write_still=True)
        MAN.append({'asset':'zinpia-eyes','file':'zinpia-eyes-render-front.png','label':'ZinPia_Doe_Eyes_Sunny_Head.zip  doe 5.png (gray) on the head\'s own eye mesh (front)','kind':'render'})
        INFO['zinpia-eyes']={'label':'ZinPia_Doe_Eyes_Sunny_Head.zip','textures':sorted(os.listdir(ZP)) if os.path.isdir(ZP) else []}
    except Exception as e:
        import traceback; traceback.print_exc(); INFO['zinpia-eyes']={'error':str(e)}
    json.dump({'renders':MAN,'info':INFO},open(O+'/manifest.json','w'),indent=1,default=str)
eyes_job()
# 3 hair meshes
def a_blowcards(sc):
    objs=imp_fbx(IN+"/Blowout Nikkie's haircards.fbx")
    for o in objs:
        if o.type=='MESH':
            for s in o.material_slots:
                if s.material: set_tex(s.material,IN+'/Textures/B&W.png',alpha=True); s.material.blend_method='HASHED'
    return objs,['Textures/B&W.png (alpha)']
job('blowout-haircards',"Blowout Nikkie's haircards.fbx  [Textures/B&W.png with alpha]",a_blowcards)
def a_blowsolid(sc):
    objs=imp_fbx(IN+'/Blowout Solid textures.fbx'); return objs,['(materials as in the FBX)']
job('blowout-solid',"Blowout Solid textures.fbx  [materials as in the FBX]",a_blowsolid)
def a_umeko(sc):
    objs=imp_fbx(IN+'/assets/hair_umeko_gift.fbx'); return objs,['(materials as in the FBX)']
job('umeko-hair',"hair_umeko_gift.fbx  [materials as in the FBX]",a_umeko)
# 4 clothes
def a_shorts(sc):
    objs=imp_fbx(IN+'/Booty Shorts by Beanie.fbx')
    for o in objs:
        if o.type=='MESH':
            for s in o.material_slots:
                if s.material and not any(n.type=='TEX_IMAGE' and n.image and n.image.size[0]>0 for n in s.material.node_tree.nodes): set_tex(s.material,IN+'/Textures/Colors/Black.png')
    return objs,['Textures/Colors/Black.png (+ Textures/Main AO/Roughness)']
job('booty-shorts',"Booty Shorts by Beanie.fbx  [Textures/Colors/Black.png]",a_shorts)
def a_outfit(sc):
    objs=imp_fbx(IN+'/Outfitriggedpanda.fbx'); return objs,['(materials as in the FBX)']
job('outfit-bra-shirt',"Outfitriggedpanda.fbx  [Bra + shirt, materials as in the FBX]",a_outfit)
def a_shirt(sc):
    objs=imp_fbx(IN+'/Outfitriggedpanda.fbx')
    for o in list(objs):
        if o.type=='MESH' and o.name=='Bra': bpy.data.objects.remove(o); objs.remove(o)
    for o in objs:
        if o.type=='MESH':
            for s in o.material_slots:
                if s.material: set_tex(s.material,IN+'/Tshirt-BasicGrey.png')
    return objs,['Tshirt-BasicGrey.png']
job('outfit-shirt-grey',"Outfitriggedpanda.fbx shirt  [Tshirt-BasicGrey.png]",a_shirt)
def a_bra(sc):
    objs=imp_fbx(IN+'/Outfitriggedpanda.fbx')
    for o in list(objs):
        if o.type=='MESH' and o.name!='Bra': bpy.data.objects.remove(o); objs.remove(o)
    return objs,['(materials as in the FBX)']
job('outfit-bra',"Outfitriggedpanda.fbx  Bra alone",a_bra)
log('DONE')
import sys as _s; _s.stdout.flush(); os._exit(0)
