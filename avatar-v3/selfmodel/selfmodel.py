# ======================= Jena body self-model (worker 41c5b341, Oct 19 2026) =======================
# Reusable on ANY motion/pose: joint limits, colliders (head+hair shell, vertex body contact), COM + ball-of-foot support,
# multi-view self-check (9 views: each detector reads the view(s) where it is observable), QC flags with the view that caught them.
# exec'd after anim10c/contact.py (needs PB, BODY, arm_co, body_co, FOOTV, HANDV, foot_stats, target_bvh, sdist, head_shell_bvh).
import math as _m
SM_MASS={'Head':0.0668,'Chest':0.1545,'Spine':0.1465,'Hips':0.1247,'arm':0.0255,'elbow':0.0138,'wrist':0.0056,'leg':0.1478,'knee':0.0481,'ankle':0.0129}
SM_LIMIT={'Neck':45,'Head':50,'Spine':35,'Chest':35,'shoulder':30,'arm':175,'elbow':150,'wrist':75,'leg':130,'knee':150,'ankle':55}
SM_VIEWS=[('front',0,5),('back',180,5),('left',90,5),('right',-90,5),('q34L',45,10),('q34R',-45,10),('top',0,88),('bottom',0,-88),('mirror',0,5)]
SM_REST={}
def sm_init():
    """call ONCE with the armature in its bind pose: foot forward, knee-facing axes, sole-up axes, high-heel lift"""
    tf=(PB['Left toe'].tail-PB['Left ankle'].head); tf.z=0; fwd0=tf.normalized(); SM_REST['fwd0']=fwd0
    SM_REST['kf0']={sd:PB[sd+' knee'].matrix.to_3x3().inverted()@fwd0 for sd in ('Left','Right')}
    SM_REST['up0']={sd:PB[sd+' ankle'].matrix.to_3x3().inverted()@Vector((0,0,1)) for sd in ('Left','Right')}
    meshes_eval(True); SM_REST['heel_lift_mm']={sd:float(foot_stats(sd,0.0)['heel_mm']-foot_stats(sd,0.0)['ball_mm']) for sd in ('Left','Right')}; meshes_eval(False)
    return SM_REST
def sm_ankle(sd):
    """(twist, inversion) deg: foot direction vs the knee's facing about the shin; shin leaning across the sole (+ = inversion)"""
    a=(PB[sd+' knee'].tail-PB[sd+' knee'].head).normalized()
    kf=PB[sd+' knee'].matrix.to_3x3()@SM_REST['kf0'][sd]; ff=(PB[sd+' toe'].tail-PB[sd+' ankle'].head) if sd+' toe' in PB else (PB[sd+' ankle'].tail-PB[sd+' ankle'].head)
    kp=(kf-a*kf.dot(a)); fp=(ff-a*ff.dot(a))
    if kp.length<1e-6 or fp.length<1e-6: return 0.0,0.0
    kp.normalize(); fp.normalize(); tw=_m.degrees(_m.atan2(kp.cross(fp).dot(a),kp.dot(fp)))
    n=PB[sd+' ankle'].matrix.to_3x3()@SM_REST['up0'][sd]; lat=ff.normalized().cross(n).normalized(); sgo=1.0 if sd=='Left' else -1.0
    return round(tw,1),round(_m.degrees(_m.asin(max(-1,min(1,a.dot(lat)))))*sgo,1)
def sm_com():
    tot=0.0; acc=Vector((0,0,0))
    for k,m_ in SM_MASS.items():
        names=[k] if k in ('Head','Chest','Spine','Hips') else ['Left '+k,'Right '+k]
        for n in names:
            if n not in PB: continue
            b=PB[n]; acc+=((b.head+b.tail)/2)*m_; tot+=m_
    return acc/max(tot,1e-6)
def _hull2(P):
    P=sorted(set((round(float(x),5),round(float(y),5)) for x,y in P))
    if len(P)<3: return P
    def cr(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];up=[]
    for p in P:
        while len(lo)>=2 and cr(lo[-2],lo[-1],p)<=0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up)>=2 and cr(up[-2],up[-1],p)<=0: up.pop()
        up.append(p)
    return lo[:-1]+up[:-1]
def _poly_sd(H,q):
    """signed distance (m) of 2D point q to convex polygon H (CCW): + inside"""
    if len(H)<3: return -1.0
    d=1e9
    for i in range(len(H)):
        a=H[i]; b=H[(i+1)%len(H)]; ex,ey=b[0]-a[0],b[1]-a[1]; L=_m.hypot(ex,ey) or 1e-9
        d=min(d,(ex*(q[1]-a[1])-ey*(q[0]-a[0]))/L)   # CCW hull: + left of every edge = inside; nearest edge = the margin
    return d
def sm_support(floor_z,tol=None,co=None):
    """footprint that bears weight: sole verts within the model's own heel lift + 3 mm of the floor (high-heel foot: ball + toes, and the heel at its natural lift)"""
    if tol is None: tol=(max(SM_REST.get('heel_lift_mm',{}).values() or [0.0])+3.0)/1000.0
    co=body_co() if co is None else co; pts=[]
    for sd in ('Left','Right'):
        f=co[FOOTV[sd]]; f=f[f[:,2]<floor_z+tol]; pts+=[(p[0],p[1]) for p in f]
    return _hull2(pts),len(pts)
def sm_rel_angle(n):
    """rotation (deg) of bone n relative to its parent, measured against the bind pose"""
    b=PB[n]; q=b.matrix_basis.to_quaternion(); return _m.degrees(2*_m.acos(max(-1.0,min(1.0,abs(q.w)))))
def sm_knee_flex(sd):
    t=(PB[sd+' leg'].tail-PB[sd+' leg'].head).normalized(); s_=(PB[sd+' knee'].tail-PB[sd+' knee'].head).normalized(); return _m.degrees(t.angle(s_))
SM_TWIST={'Neck':70,'Head':80,'Spine':45,'Chest':45,'shoulder':30,'arm':95,'elbow':170,'wrist':170,'leg':50,'knee':35,'ankle':35}
def sm_swing_twist(n):
    """bone n vs its bind pose, relative to its parent: (swing deg = bend of the bone's own axis, twist deg = roll about it)"""
    q=PB[n].matrix_basis.to_quaternion(); t=q.copy(); t.x=0.0; t.z=0.0
    if t.magnitude<1e-9: return round(_m.degrees(2*_m.acos(min(1.0,abs(q.w)))),1),0.0
    t.normalize(); sw=q@t.inverted()
    return round(_m.degrees(2*_m.acos(min(1.0,abs(sw.w)))),1),round(_m.degrees(2*_m.acos(min(1.0,abs(t.w)))),1)
def sm_joints():
    out={}
    for k,lim in SM_LIMIT.items():
        names=[k] if k in ('Neck','Head','Spine','Chest') else ['Left '+k,'Right '+k]
        for n in names:
            if n in PB:
                sw,tw=sm_swing_twist(n); out[n]={'swing':sw,'swing_lim':lim,'twist':tw,'twist_lim':SM_TWIST[k]}
    return out
def sm_view_basis(az,el):
    d=Vector((_m.sin(_m.radians(az))*_m.cos(_m.radians(el)),-_m.cos(_m.radians(az))*_m.cos(_m.radians(el)),_m.sin(_m.radians(el))))   # camera position direction (from target)
    fwd=-d; up0=Vector((0,0,1)) if abs(el)<80 else Vector((0,1,0))*(1 if el>0 else -1)
    r=fwd.cross(up0).normalized(); u=r.cross(fwd).normalized(); return r,u,d
SM_JOINTS2D=['Hips','Spine','Chest','Neck','Head','Left arm','Left elbow','Left wrist','Right arm','Right elbow','Right wrist','Left leg','Left knee','Left ankle','Left toe','Right leg','Right knee','Right ankle','Right toe']
def sm_project(az,el,mirror=False):
    r,u,d=sm_view_basis(az,el); P={}
    for n in SM_JOINTS2D:
        if n not in PB: continue
        for tag,v in (('h',PB[n].head),('t',PB[n].tail)):
            x=v.dot(r); y=v.dot(u); P[n+':'+tag]=(round(-x if mirror else x,4),round(y,4))
    return P
def sm_ang2(a,b):
    return _m.degrees(_m.atan2(a[0]*b[1]-a[1]*b[0],a[0]*b[0]+a[1]*b[1]))
def sm_selfcheck(floor_z,seated=False,src=None,co=None):
    """one frame/pose: every detector, measured in the view(s) where it is observable. returns (measures, flags[{det,view,value,limit,where}])"""
    co=body_co() if co is None else co; M={}; F=[]
    V={nm:sm_project(az,el,nm=='mirror') for nm,az,el in SM_VIEWS}
    def p(vn,n,t='h'): return V[vn].get(n+':'+t)
    # FRONT: knee alignment / cowboy (knees wider than feet), frontal knee angle
    fr=V['front']
    if p('front','Left knee') and p('front','Right knee'):
        kg=abs(p('front','Left knee')[0]-p('front','Right knee')[0]); ag=abs(p('front','Left ankle')[0]-p('front','Right ankle')[0])
        M['front_knee_minus_ankle_gap_cm']=round((kg-ag)*100,1)
        if not seated and kg-ag>0.06: F.append({'det':'COWBOY','view':'front','value':round((kg-ag)*100,1),'limit':6.0})
        for sd in ('Left','Right'):
            h=p('front',sd+' leg'); k=p('front',sd+' knee'); a=p('front',sd+' ankle')
            v1=(k[0]-h[0],k[1]-h[1]); v2=(a[0]-k[0],a[1]-k[1]); M[f'front_knee_valgus_{sd[0]}']=round(sm_ang2(v1,v2),1)
    # SIDE: knee hyperextension, plantar flexion, spine curve (sagittal) ; left/right views
    for sd,vn in (('Left','left'),('Right','right')):
        h=p(vn,sd+' leg'); k=p(vn,sd+' knee'); a=p(vn,sd+' ankle'); t=p(vn,sd+' toe','t')
        if None in (h,k,a,t): continue
        v1=(k[0]-h[0],k[1]-h[1]); v2=(a[0]-k[0],a[1]-k[1]); v3=(t[0]-a[0],t[1]-a[1])
        kf=sm_ang2(v1,v2); M[f'side_knee_bend_{sd[0]}']=round(kf,1)
        pf=abs(sm_ang2(v2,v3)); M[f'side_ankle_shin_foot_{sd[0]}']=round(pf,1)
    sp=[p('left',n) for n in ('Hips','Spine','Chest','Neck','Head')]
    if None not in sp:
        segs=[(sp[i+1][0]-sp[i][0],sp[i+1][1]-sp[i][1]) for i in range(4)]; M['side_spine_bends']=[round(sm_ang2(segs[i],segs[i+1]),1) for i in range(3)]
    # TOP: foot direction vs knee direction ; balance (COM vs ball-of-foot support)
    for sd in ('Left','Right'):
        try:
            tw,inv=sm_ankle(sd); M[f'ankle_twist_{sd[0]}']=tw; M[f'ankle_inv_{sd[0]}']=inv
            if abs(tw)>15: F.append({'det':'ANKLE','view':'top','what':'foot vs knee direction','side':sd,'value':tw,'limit':15})
            if inv>15 or inv<-10: F.append({'det':'ANKLE','view':'front','what':'inversion/eversion','side':sd,'value':inv,'limit':[15,-10]})
        except Exception: pass
    com=sm_com(); M['com']=[round(com.x,4),round(com.y,4),round(com.z,4)]
    if not seated:
        H,n=sm_support(floor_z,co=co); sdm=_poly_sd(H,(com.x,com.y)) if len(H)>=3 else None
        M['balance_margin_cm']=round(sdm*100,1) if sdm is not None else None; M['support_pts']=n; M['support_poly']=[(round(a,4),round(b,4)) for a,b in H]
        if sdm is not None and sdm<-0.01: F.append({'det':'BALANCE','view':'top','value':round(sdm*100,1),'limit':-1.0})
    # BOTTOM: feet through the floor / contact patch
    for sd in ('Left','Right'):
        fs=foot_stats(sd,floor_z,co); M[f'foot_{sd[0]}']=fs
        if fs['below_verts']>0: F.append({'det':'FLOOR','view':'bottom','side':sd,'value':fs['min_mm'],'limit':0})
    # SKELETON SANITY: joint limits (any view; recorded under the side view)
    J=sm_joints(); M['joints']=J
    for n,j_ in J.items():
        if n.endswith('ankle') and M.get('foot_'+n[0],{}).get('min_mm',0)>20: continue   # pointed foot off the floor: plantar flexion allowed (rule)
        if j_['swing']>j_['swing_lim']: F.append({'det':'LIMIT','view':'side','joint':n,'what':'bend','value':j_['swing'],'limit':j_['swing_lim']})
        if j_['twist']>j_['twist_lim']: F.append({'det':'LIMIT','view':'front','joint':n,'what':'twist','value':j_['twist'],'limit':j_['twist_lim']})
    for sd in ('Left','Right'):
        try:
            kf=sm_knee_flex(sd)
            if kf>150: F.append({'det':'LIMIT','view':'side','joint':sd+' knee','value':round(kf,1),'limit':150})
        except Exception: pass
    # CLIP: head shell (back/top), hand vs hand, hands vs body (front)
    try:
        Tsh=head_shell_bvh()
        for sd in ('Left','Right'):
            hs=hand_stats(sd,Tsh,co); M[f'hand_vs_head_shell_{sd[0]}']=hs
            if hs['pen_verts']>0: F.append({'det':'CLIP','view':'back+top','what':'hand inside head/hair shell','side':sd,'value':hs['pen_mm'],'verts':hs['pen_verts']})
    except Exception as ex: M['shell_error']=str(ex)[:120]
    for sd,o_ in (('Left','Right'),('Right','Left')):
        try:
            To=target_bvh(['Body'],frozenset({'LARM' if o_=='Right' else 'RARM','CORE','HEAD','LLEG','RLEG'}),near=PB[o_+' wrist'].head,rad=0.16)
            if To is None: continue
            hs=hand_stats(sd,To,co); M[f'hand_vs_hand_{sd[0]}']=hs
            if hs['pen_verts']>20: F.append({'det':'CLIP','view':'front','what':'hand inside other hand/arm','side':sd,'value':hs['pen_mm'],'verts':hs['pen_verts']})
        except Exception: pass
    M['views2d']=V
    return M,F
def sm_render_views(path_fmt,ctr,size,res=(360,480),floor_obj=None):
    """low-res workbench renders of the 9 self-check views (bottom view: floor hidden, looking up)"""
    eng=sc.render.engine; rx,ry=sc.render.resolution_x,sc.render.resolution_y
    sc.render.engine='BLENDER_WORKBENCH'; sc.render.resolution_x,sc.render.resolution_y=res
    try:
        sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL'
    except Exception: pass
    out={}
    for nm,az,el in SM_VIEWS:
        if floor_obj is not None: floor_obj.hide_render=(nm=='bottom')
        cam.data.type='ORTHO'; cam.data.ortho_scale=size
        if nm=='mirror': out[nm]=dict(out['front'],mirror=True); continue
        r,u,d=sm_view_basis(az,el); cam.location=ctr+d*4.0; cam.rotation_euler=Matrix((r,u,d)).transposed().to_euler()
        upd(); fp=path_fmt.format(nm); render(fp); out[nm]={'path':fp,'right':[round(x,5) for x in r],'up':[round(x,5) for x in u],'ctr':[round(x,5) for x in ctr],'scale':size,'res':list(res)}
    if floor_obj is not None: floor_obj.hide_render=False
    cam.data.type='PERSP'; sc.render.engine=eng; sc.render.resolution_x,sc.render.resolution_y=rx,ry
    return out

def _sm_set_rot(n,R):
    if n not in PB: return
    q=(R@PB[n].matrix.to_3x3().inverted()).to_quaternion(); qrot(n,q)
def sm_fix_ankles(floor_z,sides=('Left','Right')):
    """AUTO-FIX ANKLE: foot turned toward its knee (twist <=15) and no rolled ankle (inv <=15, ev <=10); a foot that was on the floor is re-grounded (ball 0.6 mm)"""
    rep={}
    def _out(tw,inv): return max(0.0,abs(tw)-15.0)+max(0.0,inv-15.0)+max(0.0,-10.0-inv)
    for sd in sides:
        b=sm_ankle(sd); meshes_eval(True); fs0=foot_stats(sd,floor_z); meshes_eval(False); grounded=fs0['min_mm']<3.0
        if _out(*b)<=0: continue
        for it in range(5):
            tw,inv=sm_ankle(sd)
            if _out(tw,inv)<=0: break
            a=(PB[sd+' knee'].tail-PB[sd+' knee'].head).normalized()
            if abs(tw)>15.0:
                ex=tw-_m.copysign(13.0,tw); wrot_v(sd+' ankle',-ex,a)
                if abs(sm_ankle(sd)[0])>abs(tw): wrot_v(sd+' ankle',2*ex,a)
            tw,inv=sm_ankle(sd)
            if inv>15.0 or inv<-10.0:
                lim=13.0 if inv>0 else -8.0; d=inv-lim
                ff=((PB[sd+' toe'].tail if sd+' toe' in PB else PB[sd+' ankle'].tail)-PB[sd+' ankle'].head).normalized()
                wrot_v(sd+' ankle',d,ff)
                if abs(sm_ankle(sd)[1]-lim)>abs(d): wrot_v(sd+' ankle',-2*d,ff)
        fs=None
        if grounded:
            for k in range(5):
                meshes_eval(True); fs=foot_stats(sd,floor_z); meshes_eval(False); dz=(0.6-fs['min_mm'])/1000.0
                if abs(dz)<0.0004: break
                Ra={n_:PB[n_].matrix.to_3x3().copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
                kn=PB[sd+' knee'].head.copy(); pole=kn+(kn-(PB[sd+' leg'].head+PB[sd+' ankle'].head)/2).normalized()*0.5
                ik2(sd+' leg',sd+' knee',PB[sd+' ankle'].head+Vector((0,0,dz)),pole)
                for n_,R_ in Ra.items(): _sm_set_rot(n_,R_)
        upd(); rep[sd]={'before':b,'after':sm_ankle(sd),'grounded':grounded,'min_mm_after':(fs or {}).get('min_mm')}
    return rep
def sm_autofix(floor_z,seated=False,passes=3):
    """detect -> fix -> re-detect (<=3 passes). returns (final measures, final flags, history [{pass, flags_before, fixed}])"""
    hist=[]
    for p_ in range(passes):
        M_,F_=sm_selfcheck(floor_z,seated)
        fixable=[f for f in F_ if f['det']=='ANKLE']
        hist.append({'pass':p_,'flags':[{k:v for k,v in f.items()} for f in F_]})
        if not fixable: return M_,F_,hist
        hist[-1]['ankle_fix']=sm_fix_ankles(floor_z,tuple(sorted({f['side'] for f in fixable})))
    M_,F_=sm_selfcheck(floor_z,seated); hist.append({'pass':passes,'flags':F_}); return M_,F_,hist
