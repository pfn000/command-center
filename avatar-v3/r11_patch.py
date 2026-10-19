import sys,os
p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'assemble.py'); s=open(p).read()
ins=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'r11_insert.py')).read()
A="# ---------- 6. ONE armature: merge the head's and the hair's bones into Panda's"
assert s.count(A)==1, 'anchor count %d'%s.count(A)
assert 'r11_shoulder_weights' not in s
s=s.replace(A,ins+A)
K="out['rep']={k_:rep.get(k_) for k_ in ('posed_converge',"
if s.count(K)==1: s=s.replace(K,"out['rep']={k_:rep.get(k_) for k_ in ('r11_shoulder_weights','posed_converge',")
open(p,'w').write(s); print('R11 PATCHED', len(s))
