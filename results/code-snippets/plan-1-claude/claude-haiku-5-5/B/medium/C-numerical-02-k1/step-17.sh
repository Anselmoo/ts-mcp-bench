cd /tmp/tsbench-run-aa74wow9/d7 2>/dev/null || cd /tmp/tsbench-run-aa74wow9/d7; cp /tmp/tsbench-run-aa74wow9/d7/mats.npz . 2>/dev/null; python3 -c "
import numpy as np
d=np.load('mats.npz'); Hd,H2,H4,S2=d['Hd'],d['H2'],d['H4'],d['S2']
def levels(Dq,F2,F4):
    H=Dq*Hd+F2*H2+F4*H4
    w,v=np.linalg.eigh(H+50*S2)
    S=np.real(np.einsum('in,ij,jn->n',v,S2,v))
    E=np.real(np.einsum('in,ij,jn->n',v,H,v))
    return E,S
import collections
for Dq,F2,F4 in [(900,1000,600),(1000,800,500),(900,1000,0),(0,1000,600)]:
    E,S=levels(Dq,F2,F4)
    q=np.sort(E[np.abs(S-3.75)<1e-3])
    vals=[]
    for e in q:
        if not vals or abs(e-vals[-1])>1e-6: vals.append(e)
    print(Dq,F2,F4,np.round(np.array(vals)-vals[0],0), collections.Counter(np.round(S,2)).most_common(3))
"