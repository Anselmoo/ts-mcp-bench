cat > check_d2.py << 'EOF'
import numpy as np, itertools
import ts
from ts import V, nz, annih, create, Fv
def spectrum(n, F):
    import importlib
    dets = list(itertools.combinations(range(10), n)); idx={d:i for i,d in enumerate(dets)}
    # rebuild V with same F
    Vm = ts.V
    H = np.zeros((len(dets),len(dets)))
    for m,s in enumerate(dets):
        for (i,j,k,l) in ts.nz:
            r=annih(k,s)
            if r is None: continue
            s1,t=r; r=annih(l,t)
            if r is None: continue
            s2,t=r; r=create(j,t)
            if r is None: continue
            s3,t=r; r=create(i,t)
            if r is None: continue
            s4,t=r
            H[idx[t],m]+=0.5*Vm[i,j,k,l]*s1*s2*s3*s4
    return H, dets
# d2 check: Racah B=1, C=C
for C in [0.0, 1.0]:
    F={0:0,2:49+7*C,4:12.6*C}
    Vm=np.zeros((10,10,10,10))
    for i,j,k,l in itertools.product(range(10),repeat=4):
        if i%2!=k%2 or j%2!=l%2: continue
        a,b,c,d=i//2,j//2,k//2,l//2
        Vm[i,j,k,l]=sum(F[q]*ts.G[q][a*5+c,b*5+d] for q in (0,2,4))
    ts.V=Vm
    ts.nz=[(i,j,k,l) for i,j,k,l in itertools.product(range(10),repeat=4) if abs(Vm[i,j,k,l])>1e-12]
    H,dets=spectrum(2,F)
    S2=None
    w=np.linalg.eigvalsh(H)
    print("C=",C, np.round(np.unique(np.round(w,6)),4))
EOF
python3 check_d2.py 2>/dev/null | tail -3