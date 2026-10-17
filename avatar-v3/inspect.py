
import bpy, sys, os, json, math, mathutils
argv=sys.argv[sys.argv.index('--')+1:]; IN,OUT=argv[0],argv[1]; A=IN+'/assets'
def log(*a): print('[v3]',*a,flush=True)
rep={}
def tris(o):
    if o.type!='MESH': return 0
    return sum(len(p.vertices)-2 for p in o.data.polygons)
def desc(o):
    d={'type':o.type,'parent':o.parent.name if o.parent else None,'parent_bone':o.parent_bone,'loc':[round(x,3) for x in o.location],'rot':[round(x,3) for x in o.rotation_euler],'scale':[round(x,3) for x in o.scale],
       'mods':[(m.type,getattr(getattr(m,'object',None),'name',None)) for m in o.modifiers],'coll':[c.name for c in o.users_collection]}
    if o.type=='MESH':
        me=o.data; bb=[o.matrix_world@mathutils.Vector(c) for c in o.bound_box]
        d.update(verts=len(me.vertices),tris=tris(o),bbox_min=[round(min(v[i] for v in bb),3) for i in range(3)],bbox_max=[round(max(v[i] for v in bb),3) for i in range(3)],
          uvs=[u.name for u in me.uv_layers],shapekeys=[k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],vgroups=len(o.vertex_groups),vg_sample=[g.name for g in o.vertex_groups][:12])
        mats=[]
        for s in o.material_slots:
            m=s.material; imgs=[]
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type=='TEX_IMAGE' and n.image:
                        lk=[(l.to_node.type,l.to_socket.name) for l in n.outputs[0].links]
                        imgs.append((n.image.name,n.image.filepath,list(n.image.size),lk))
            mats.append({'name':m.name if m else None,'imgs':imgs})
        d['mats']=mats
    if o.type=='ARMATURE':
        d['bones']=[(b.name,b.parent.name if b.parent else None) for b in o.data.bones]
        d['nbones']=len(o.data.bones)
    return d
def snap(tag):
    rep[tag]={o.name:desc(o) for o in bpy.data.objects if o.get('_tag')==tag}
    for n,d in rep[tag].items(): log(tag,n,d['type'],'tris',d.get('tris'),'bones',d.get('nbones'),'sk',len(d.get('shapekeys',[])),'mats',[m['name'] for m in d.get('mats',[])],'bb',d.get('bbox_min'),d.get('bbox_max'),'par',d['parent'])
def tagnew(before,tag,coll):
    for o in bpy.data.objects:
        if o.name not in before:
            o['_tag']=tag
            for c in list(o.users_collection): c.objects.unlink(o)
            coll.objects.link(o)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
# BODY: append from .blend
with bpy.data.libraries.load(A+'/body_PandaFitBase_HighFlatFoot.blend',link=False) as (df,dt):
    log('blend collections',list(df.collections)); log('blend objects',list(df.objects)); log('blend images',list(df.images)[:60]); log('blend materials',list(df.materials))
    dt.objects=list(df.objects)
rep['blend_images']=[]
col=bpy.data.collections.new('body'); sc.collection.children.link(col)
for o in dt.objects:
    if o is None: continue
    o['_tag']='body'; col.objects.link(o)
snap('body')
for im in bpy.data.images: rep['blend_images'].append((im.name,im.filepath,list(im.size),im.packed_file is not None))
log('images', rep['blend_images'])
for tag,f in [('hairF','hair_female_head_hair.fbx'),('hairU','hair_umeko_gift.fbx'),('top','top_Outfitriggedpanda.fbx'),('shorts','shorts_BootyShorts_Beanie.fbx')]:
    b=set(o.name for o in bpy.data.objects); c=bpy.data.collections.new(tag); sc.collection.children.link(c)
    try: bpy.ops.import_scene.fbx(filepath=A+'/'+f)
    except Exception as e: log('FBXERR',f,e)
    tagnew(b,tag,c); snap(tag)
b=set(o.name for o in bpy.data.objects); c=bpy.data.collections.new('eye'); sc.collection.children.link(c)
try: bpy.ops.import_scene.gltf(filepath=IN+'/refs/Meshy_Jena_Eyeball.glb')
except Exception as e: log('GLBERR',e)
tagnew(b,'eye',c); snap('eye')
json.dump(rep,open(OUT+'/inspect.json','w'),indent=1,default=str)
# previews: Cycles CPU
sc.render.engine='CYCLES'; sc.cycles.samples=12; sc.cycles.device='CPU'; sc.render.resolution_x=640; sc.render.resolution_y=900
sc.render.image_settings.file_format='JPEG'
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.25,0.25,0.27,1); w.node_tree.nodes['Background'].inputs[1].default_value=1.2
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.type='ORTHO'
L=bpy.data.objects.new('sun',bpy.data.lights.new('sun','SUN')); sc.collection.objects.link(L); L.rotation_euler=(math.radians(50),0,math.radians(30)); L.data.energy=3
def frame(tags,name,view='front',pad=1.1):
    for c in sc.collection.children: 
        c.hide_render = c.name not in tags
    obs=[o for o in bpy.data.objects if o.get('_tag') in tags and o.type=='MESH' and not o.hide_render]
    if not obs: return
    pts=[o.matrix_world@mathutils.Vector(cc) for o in obs for cc in o.bound_box]
    mn=mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); mx=mathutils.Vector([max(p[i] for p in pts) for i in range(3)]); ce=(mn+mx)/2; size=max(mx.z-mn.z,(mx.x-mn.x)*900/640,(mx.y-mn.y)*900/640)
    cam.data.ortho_scale=size*pad; cam.data.clip_end=1000
    if view=='front': cam.location=(ce.x,ce.y-50,ce.z); cam.rotation_euler=(math.radians(90),0,0)
    else: cam.location=(ce.x+50,ce.y,ce.z); cam.rotation_euler=(math.radians(90),0,math.radians(90))
    sc.render.filepath=OUT+'/proof/'+name+'.jpg'
    try: bpy.ops.render.render(write_still=True); log('render',name)
    except Exception as e: log('RENDERERR',name,e)
for t in ['body','hairF','hairU','top','shorts','eye']: frame([t],'i_'+t)
frame(['body','hairF','top','shorts'],'i_all_hairF'); frame(['body','hairU','top','shorts'],'i_all_hairU'); frame(['body','hairU','top','shorts'],'i_all_side','side')
log('DONE')
