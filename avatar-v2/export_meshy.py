
import bpy, sys, json
out = sys.argv[sys.argv.index('--')+1]
rep = {'objects': []}
for o in bpy.data.objects:
    d = {'name': o.name, 'type': o.type}
    if o.type == 'MESH':
        d.update(verts=len(o.data.vertices), mats=[m.name for m in o.data.materials if m], shape_keys=(len(o.data.shape_keys.key_blocks)-1 if o.data.shape_keys else 0),
                 vgroups=len(o.vertex_groups))
    if o.type == 'ARMATURE': d['bones'] = len(o.data.bones)
    rep['objects'].append(d)
for o in bpy.data.objects: o.hide_set(False); o.hide_viewport = False
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_apply=True, export_morph=False, export_animations=False, export_yup=True)
json.dump(rep, open(out + '.report.json','w'), indent=1); print(json.dumps(rep)[:2000])
