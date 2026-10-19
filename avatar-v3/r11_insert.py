
# ---------- run 11 (Saidie 9:47 PM Oct 18 "fix that seem" = go-ahead for ONE spot): RIGHT shoulder band/sleeve junction WEIGHT TRANSFER.
#            Runs 10b/10c: puckers + 2-3 dark slashes at the front-3/4 of her right shoulder where the sleeve folds under the off-shoulder band,
#            because the band verts (farther than 30 mm from the skin) keep her outfit weights while the sleeve under them already follows the arm.
#            Fix: inside a soft spherical mask around the right band/sleeve junction (centre = right upper-arm head + R11_ALONG along the arm,
#            full strength within R11_R0, fading to 0 at R11_R1, right side only), every shirt vert takes the BODY's own weights at its nearest
#            skin point (nearest face, barycentric-interpolated = Blender's Data Transfer "Nearest Face Interpolated"), blended by the mask,
#            then a light Gaussian weight smooth inside the mask (weld twins equalized after). Mesh shape untouched; nothing outside the mask changes.
def r11_shoulder_weights(o):
    t0=_t.time(); r={}
    bn='Right arm'
    if bn not in B.data.bones: rep['r11_shoulder_weights']={'skipped':'no Right arm bone'}; return
    bb=B.data.bones[bn]; mw=np.array(B.matrix_world)
    h=(mw@np.r_[np.array(bb.head_local),1.0])[:3]; tl=(mw@np.r_[np.array(bb.tail_local),1.0])[:3]
    ax=(tl-h)/max(np.linalg.norm(tl-h),1e-9)
    c=h+ax*float(P.get('R11_ALONG',0.06)); R0=float(P.get('R11_R0',0.05)); R1=float(P.get('R11_R1',0.085))
    mid=float(np.array(B.matrix_world.translation)[0])
    X=wco(o); d=np.linalg.norm(X-c,axis=1); m=np.clip((R1-d)/max(R1-R0,1e-9),0,1)
    m[np.sign(X[:,0]-mid)!=np.sign(c[0]-mid)]=0.0
    idx=np.where(m>0)[0]
    dg=bpy.context.evaluated_depsgraph_get(); eb=BODY.evaluated_get(dg); me=eb.to_mesh(); me.calc_loop_triangles(); bmw=BODY.matrix_world
    use_ev=len(me.vertices)==len(BODY.data.vertices)
    if use_ev: V=np.array([tuple(bmw@v.co) for v in me.vertices]); F=np.array([tuple(t.vertices) for t in me.loop_triangles],dtype=np.int64)
    eb.to_mesh_clear()
    if not use_ev:
        me2=BODY.data; me2.calc_loop_triangles(); V=wco(BODY); F=np.array([tuple(t.vertices) for t in me2.loop_triangles],dtype=np.int64)
    T=BVHTree.FromPolygons(V.tolist(),F.tolist())
    bones=set(b.name for b in B.data.bones); WB=_vw(BODY); WB=[{k:w for k,w in d_.items() if k in bones} for d_ in WB]
    from mathutils.geometry import barycentric_transform as _btf
    W0=_vw(o); Wl=[dict(w) for w in W0]; dist_mm=[]
    for i in idx:
        loc,nr,fi,dd=T.find_nearest(Vector(tuple(X[i])))
        if loc is None: continue
        tri=F[fi]; bc=_btf(loc,Vector(tuple(V[tri[0]])),Vector(tuple(V[tri[1]])),Vector(tuple(V[tri[2]])),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        wb={}
        for k_,c_ in zip(tri,bc):
            for g,w in WB[k_].items(): wb[g]=wb.get(g,0)+max(c_,0)*w
        s=sum(wb.values())
        if s<=0: continue
        a=float(m[i]); new={}
        for k,w in Wl[i].items(): new[k]=new.get(k,0)+(1-a)*w
        for k,w in wb.items(): new[k]=new.get(k,0)+a*w/s
        Wl[i]=new; dist_mm.append(dd*1000)
    # light smooth inside the mask (Gaussian over rest-space neighbours, strength = mask * R11_SMOOTH_K)
    names=sorted(set(k for w in Wl for k in w)); gi={k:j for j,k in enumerate(names)}; n=len(Wl)
    Wm=np.zeros((n,len(names)))
    for i,w in enumerate(Wl):
        for k,x in w.items(): Wm[i,gi[k]]=x
    s_=Wm.sum(1); s_[s_==0]=1; Wm/=s_[:,None]
    kd=KDTree(n)
    for i,p in enumerate(X): kd.insert(Vector(tuple(p)),i)
    kd.balance()
    Rs=float(P.get('R11_SMOOTH_R',0.012)); sg=float(P.get('R11_SMOOTH_SIG',0.006)); K=float(P.get('R11_SMOOTH_K',0.5))
    NB={}
    for i in idx:
        hits=kd.find_range(Vector(tuple(X[i])),Rs); NB[i]=(np.array([h_[1] for h_ in hits],dtype=np.int64),np.exp(-np.array([h_[2] for h_ in hits])**2/(2*sg*sg)))
    for it in range(int(P.get('R11_SMOOTH',2))):
        Wn=Wm.copy()
        for i in idx:
            j,w=NB[i]; avg=(Wm[j]*w[:,None]).sum(0)/w.sum(); k_=K*m[i]; Wn[i]=(1-k_)*Wm[i]+k_*avg
        Wm=Wn
    l1=[]
    for i in idx:
        dct=_norm4({names[k]:float(Wm[i,k]) for k in range(len(names)) if Wm[i,k]>0.002})
        keys=set(dct)|set(W0[i]); s0=sum(W0[i].values()) or 1
        l1.append(sum(abs(dct.get(k,0)-W0[i].get(k,0)/s0) for k in keys)); Wl[i]=dct
    out_mask=np.where(m<=0)[0]
    _write_w(o,Wl)
    r['equalized_weld_verts']=weights_equalize(o) if P.get('WELD',True) else 0
    clean_weights(o)
    W1=_vw(o); outside_changed=0
    for i in out_mask:
        a_=W0[i]; b_=W1[i]; sa=sum(a_.values()) or 1; sb=sum(b_.values()) or 1
        if any(abs(a_.get(k,0)/sa-b_.get(k,0)/sb)>1e-3 for k in set(a_)|set(b_)): outside_changed+=1
    l1=np.array(l1) if l1 else np.zeros(1)
    r.update({'bone':bn,'centre':[round(float(x),4) for x in c],'along_m':float(P.get('R11_ALONG',0.06)),'r_full_mm':R0*1000,'r_zero_mm':R1*1000,
              'mask_verts':int(len(idx)),'mask_full_verts':int((m>=0.999).sum()),'of':int(n),'skin_dist_mm_med':round(float(np.median(dist_mm)) if dist_mm else 0,2),
              'skin_dist_mm_max':round(float(max(dist_mm)) if dist_mm else 0,2),'weight_change_L1_mean':round(float(l1.mean()),3),'weight_change_L1_max':round(float(l1.max()),3),
              'verts_changed_L1_gt_0.05':int((l1>0.05).sum()),'outside_mask_changed_verts':int(outside_changed),'smooth_iters':int(P.get('R11_SMOOTH',2)),
              'smooth_k':K,'body_eval_mesh':use_ev,'secs':round(_t.time()-t0,1)})
    rep['r11_shoulder_weights']=r; log('R11 shoulder weights',json.dumps(r,default=str))
if SHIRT is not None and P.get('R11_W',False):
    try: r11_shoulder_weights(SHIRT)
    except Exception as e: traceback.print_exc(); log('R11ERR',e); rep['r11_shoulder_weights_error']=str(e); raise
