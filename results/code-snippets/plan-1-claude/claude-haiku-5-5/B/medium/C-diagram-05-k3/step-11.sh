cd <SANDBOX_TMP>/ts && cat > final.py << 'EOF'
from run3 import *
import numpy as np, hashlib, os
names = {'A1':'A1g','A2':'A2g','E':'Eg','T1':'T1g','T2':'T2g'}
# parent labels by (block, irrep, sorted index), from Dq->0+ ordering
lab = {
 ('4','T1'):['4T1g(F)','4T1g(P)'],
 ('4','T2'):['4T2g(F)'],
 ('4','A2'):['4A2g(F)'],
 ('2','A1'):['2A1g(G)'],
 ('2','A2'):['2A2g(F)'],
 ('2','E'): ['2Eg(G)','2Eg(H)','2Eg(D)(1)','2Eg(D)(2)'],
 ('2','T1'):['2T1g(G)','2T1g(P)','2T1g(H)(1)','2T1g(H)(2)','2T1g(F)'],
 ('2','T2'):['2T2g(G)','2T2g(H)','2T2g(D)(1)','2T2g(F)','2T2g(D)(2)'],
}
# check block sizes vs labels at eps
sp0 = block_spectrum(1e-6)
for k,v in sp0.items():
    assert len(v)==len(lab[(k[0],k[1])]), (k, len(v))
def levels_at(dq):
    sp = block_spectrum(dq)
    out=[]
    for key,levs in sp.items():
        for k,(e,L) in enumerate(levs):
            out.append((e, lab[(key[0],key[1])][k]))
    out.sort(key=lambda t:t[0])
    e0 = out[0][0]
    return [(e-e0, name) for e,name in out]
# tie-break at Dq=0 by tiny-Dq ordering: sort key = (E at Dq=0, E at Dq=1e-4)
eps=1e-4
lo = levels_at(eps); l0 = levels_at(0.0)
d_eps = {n:e for e,n in lo}
l0s = sorted(l0, key=lambda t:(round(t[0],6), d_eps[t[1]]))
print('Dq=0 first 8:', [(n, round(e,4)) for e,n in l0s[:8]])
table = {}
for dq in np.arange(0,4.01,0.5):
    if dq==0: L = l0s
    else: L = levels_at(dq)
    table[round(dq,1)] = L[:6]
    print(f"Dq/B={dq:.1f}:", ", ".join(f"{n} {e:.4f}" for e,n in L[:6]))
import pickle
pickle.dump({'table':table}, open('table.pkl','wb'))
EOF
python3 final.py 2>&1 | grep -v "block dim"