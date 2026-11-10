cat > chk2.py << 'EOF'
import numpy as np, itertools
src=open('run_d3.py').read().split('dets=[frozenset')[0]
exec(src)
def mk(nel):
    dets=[frozenset(c) for c in itertools.combinations(range(N),nel)]
    idx={d:i for i,d in enumerate(dets)}; return dets,idx
def build(nel,V,h=None):
    dets,idx=mk(nel); D=len(dets)
    H=np.zeros((D,D),complex)
    for J,d in enumerate(dets):
        for a,b,c,e in itertools.product(range(N),repeat=4):
            if so[a][1]!=so[c][1] or so[b][1]!=so[e][1]: continue
            val=V[ms.index(so[a][0]),ms.index(so[b][0]),ms.index(so[c][0]),ms.index(so[e][0])]
            if abs(val)<1e-13: continue
            ns,s=apply([('c',a),('c',b),('a',e),('a',c)],d)
            if ns is None: continue
            H[idx[ns],J]+=0.5*val*s
    return dets,H
for nel in (2,3):
    for lab,V in (('F2',V2),('F4',V4)):
        dets,H=build(nel,V)
        Sz=sum(1 for d in dets)  # all
        up=[i for i,d in enumerate(dets) if all(so[k][1]==+1 for k in d)]
        ev=np.round(np.linalg.eigvalsh(H[np.ix_(up,up)].real),6)
        # d2 triplet: all-up sector 2 electrons
        vals,counts=np.unique(ev,return_counts=True)
        print(nel,lab,'all-up sector levels',list(zip(vals,counts)), 'trace all', np.round(np.trace(H.real),6))
EOF
python3 chk2.py