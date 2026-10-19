
# Jena dance4 RIG27 (big-fix pass, Oct 19 2026). Saidie: "she needs like 27 bones minimum" + pelvis triangle, spine x3-4, sternum, neck x2, heel/ball/toe.
# Splits Spine, Chest and Neck in two (vertex weights split smoothly along each bone) and adds driven helper bones.
# Rest shape is untouched: an armature only moves vertices away from the rest pose, and the rest pose is not changed.
def _rig27():
    arm=B; ad=arm.data; AWi=arm.matrix_world.inverted()
    SPLIT=(('Spine','Spine2'),('Chest','UpperChest'),('Neck','Neck2'))
    bl={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in ad.bones}
    # 1) weights: lower half keeps w*(1-s), new upper half gets w*s, s = smoothstep along the bone (0.25..0.75)
    wlog={}
    for o in [o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers)]:
        M_=AWi@o.matrix_world; vgs=o.vertex_groups
        for lo,hi in SPLIT:
            g=vgs.get(lo)
            if g is None: continue
            gh=vgs.get(hi) or vgs.new(name=hi); h,t=bl[lo]; d=t-h; L2=max(d.length_squared,1e-9); n=0
            gi=g.index
            for v in o.data.vertices:
                w=None
                for ge in v.groups:
                    if ge.group==gi: w=ge.weight; break
                if not w: continue
                p=M_@v.co; u=(p-h).dot(d)/L2; x=min(1.0,max(0.0,(u-0.25)/0.5)); s=x*x*(3-2*x)
                g.add([v.index],w*(1-s),'REPLACE'); gh.add([v.index],w*s,'REPLACE'); n+=1
            wlog[f'{o.name}:{lo}->{hi}']=n
    log('RIG27 weight split (verts per mesh/bone)',wlog)
    # 2) mesh landmarks for the feet: heel, ball, toe tip from her real foot verts (dominant group ankle/toe)
    FEETP={}
    bo=bpy.data.objects['Body']; Mb=AWi@bo.matrix_world; vgn={g.index:g.name for g in bo.vertex_groups}
    for sd in ('Left','Right'):
        P_=[]
        for v in bo.data.vertices:
            best=None; w=0.0
            for ge in v.groups:
                if ge.weight>w: w=ge.weight; best=vgn.get(ge.group)
            if best in (sd+' ankle',sd+' toe'): P_.append(tuple(Mb@v.co))
        P_=np.array(P_); zmin=P_[:,2].min(); sole=P_[P_[:,2]<zmin+0.012]
        tip=P_[np.argmin(P_[:,1])]                     # front-most (she faces -Y)
        low=P_[P_[:,2]<zmin+0.03]; heel=low[np.argmax(low[:,1])]   # back-most low point
        th=bl[sd+' toe'][0]; dd=np.linalg.norm(sole[:,:2]-np.array([th.x,th.y]),axis=1); ball=sole[np.argmin(dd)]
        FEETP[sd]=dict(heel=Vector(tuple(heel)),ball=Vector(tuple(ball)),tip=Vector(tuple(tip)),zmin=float(zmin))
    # 3) edit bones
    arm.hide_viewport=False
    try: arm.hide_set(False)
    except Exception: pass
    for o in list(bpy.context.selected_objects): o.select_set(False)
    bpy.context.view_layer.objects.active=arm; arm.select_set(True); bpy.ops.object.mode_set(mode='EDIT'); eb=ad.edit_bones
    for lo,hi in SPLIT:
        b=eb[lo]; h=b.head.copy(); t=b.tail.copy(); m=(h+t)/2; kids=[c for c in b.children]
        n=eb.new(hi); n.head=m; n.tail=t; n.roll=b.roll; n.use_deform=True; n.parent=b; n.use_connect=False
        for c in kids: c.use_connect=False; c.parent=n
        b.tail=m
    hp=eb['Hips']; LL=eb['Left leg'].head.copy(); RL=eb['Right leg'].head.copy(); mid=(LL+RL)/2
    for nm,tl,leg in (('Hip_L',LL,'Left leg'),('Hip_R',RL,'Right leg')):
        n=eb.new(nm); n.head=mid.copy(); n.tail=tl.copy(); n.use_deform=False; n.parent=hp; eb[leg].use_connect=False; eb[leg].parent=n
    n=eb.new('Sacrum'); n.head=mid.copy(); n.tail=mid+Vector((0,0.075,0.03)); n.use_deform=False; n.parent=hp
    uc=eb['UpperChest']; n=eb.new('Sternum'); n.head=uc.head.copy(); n.tail=uc.head+Vector((0,-0.10,0.01)); n.use_deform=False; n.parent=uc
    snap={}
    for sd,s in (('Left','L'),('Right','R')):
        an=eb[sd+' ankle']; to=eb[sd+' toe']; fp=FEETP[sd]
        off=(Vector((to.head.x,to.head.y))-Vector((fp['ball'].x,fp['ball'].y))).length*1000
        snap[sd]={'toe_head_vs_mesh_ball_mm':round(off,1)}
        if off>8.0:   # toe joint sits over the ball of her foot (the mesh's own sole point), height kept
            to.use_connect=False; nh=Vector((fp['ball'].x,fp['ball'].y,to.head.z)); to.head=nh; snap[sd]['moved']=True
        tt=Vector((fp['tip'].x,fp['tip'].y,max(to.tail.z,fp['zmin']+0.01)))
        if (Vector((to.tail.x,to.tail.y))-Vector((tt.x,tt.y))).length>0.008: to.tail=tt; snap[sd]['tip_moved']=True
        for nm,p in (('Heel_'+s,fp['heel']),('Ball_'+s,fp['ball'])):
            n=eb.new(nm); n.head=an.head.copy(); n.tail=p.copy(); n.use_deform=False; n.parent=an
    bpy.ops.object.mode_set(mode='OBJECT')
    log('RIG27 foot snap',snap,'mesh feet',{sd:{k:[round(x,3) for x in v] if hasattr(v,'x') else v for k,v in d.items()} for sd,d in FEETP.items()})
    return FEETP
FEETP=_rig27(); PB=B.pose.bones
RIG27_DRIVEN={
 'mocap':['Hips','Spine','Spine2','Chest','UpperChest','Neck','Neck2','Head']+[f'{sd} {n}' for sd in ('Left','Right') for n in ('shoulder','arm','elbow','wrist','leg','knee','ankle')],
 'derived':['Wrist_Twist.L','Wrist_Twist.R','Left toe','Right toe','Hip_L','Hip_R','Sacrum','Sternum','Heel_L','Heel_R','Ball_L','Ball_R']}
RIG27_DRIVEN['derived']=[n for n in RIG27_DRIVEN['derived'] if n in PB]; RIG27_DRIVEN['mocap']=[n for n in RIG27_DRIVEN['mocap'] if n in PB]
RIG27_BODY=RIG27_DRIVEN['mocap']+RIG27_DRIVEN['derived']
log('RIG27 BODY BONES',len(RIG27_BODY),'mocap-driven',len(RIG27_DRIVEN['mocap']),RIG27_DRIVEN['mocap'],'derived',len(RIG27_DRIVEN['derived']),RIG27_DRIVEN['derived'],
    'fingers',len([b.name for b in PB if any(b.name.startswith(x) for x in ('Thumb','Index','Middle','Ring','Little'))]),'all bones',len(PB))
