LANES=[('DRUMS','drums',(60,200,255)),('BASS','bass',(255,140,60)),('VOCALS','vocals',(255,90,220)),('OTHER','other',(120,255,140))]
def strip(k):
    S=np.zeros((SH_,2*W,3),np.uint8); S[:]=(18,18,22); i=k; mus=LMJ['music']; aud=LMJ['audio']; n=len(mus)
    x0=150; x1=2*W-200; span=int(4*fps); lh=(SH_-30)//4
    mx={key:max(1e-3,max((m['e'].get(key) or 0) for m in mus)) for _,key,_ in LANES}
    for li,(lab,key,col) in enumerate(LANES):
        y0=12+li*lh; cv2.putText(S,lab,(14,y0+lh-12),cv2.FONT_HERSHEY_SIMPLEX,0.55,col,1,cv2.LINE_AA); cv2.line(S,(x0,y0+lh-4),(x1,y0+lh-4),(60,60,66),1)
        pts=[]
        for j in range(span):
            fi=i-span+1+j
            if 0<=fi<n: v=(mus[fi]['e'].get(key) or 0)/mx[key]; pts.append((x0+int((x1-x0)*j/(span-1)),y0+lh-4-int((lh-8)*min(1,v**0.6))))
        if len(pts)>1:
            poly=np.array(pts+[(pts[-1][0],y0+lh-4),(pts[0][0],y0+lh-4)],np.int32); ov_=S.copy(); cv2.fillPoly(ov_,[poly],col); S[:]=cv2.addWeighted(ov_,0.35,S,0.65,0); cv2.polylines(S,[np.array(pts,np.int32)],False,col,2,cv2.LINE_AA)
    for j in range(span):   # beat ticks
        fi=i-span+1+j
        if 0<=fi<n and LMJ['beat'][fi]: xx=x0+int((x1-x0)*j/(span-1)); cv2.line(S,(xx,8),(xx,SH_-18),(255,255,255) if LMJ['downbeat'][fi] else (130,130,140),1)
    cv2.line(S,(x1,6),(x1,SH_-14),(0,235,255),2)
    last=max([j for j in range(max(0,i-6),i+1) if j<n and LMJ['beat'][j]] or [-99]); pulse=max(0.0,1-(i-last)/6.0)
    cx=2*W-100; cv2.circle(S,(cx,70),int(26+16*pulse),(0,235,255) if pulse>0 else (80,80,90),-1 if pulse>0.3 else 2,cv2.LINE_AA)
    cv2.putText(S,f"{LMJ.get('tempo_bpm',0):.0f} BPM",(cx-50,135),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2,cv2.LINE_AA)
    bib=aud[min(i,n-1)].get('beat_in_bar') if aud else None
    if bib: cv2.putText(S,f"beat {bib}/4",(cx-45,165),cv2.FONT_HERSHEY_SIMPLEX,0.6,(200,200,210),1,cv2.LINE_AA)
    cv2.putText(S,'MUSIC  (stems energy, beats; no lyrics)',(x0,SH_-4),cv2.FONT_HERSHEY_SIMPLEX,0.45,(170,170,180),1,cv2.LINE_AA)
    return S
