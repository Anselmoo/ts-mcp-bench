cd /tmp/tsbench-run-7__jfl5e; cat > fit4.py << 'EOF'
import numpy as np
from scipy.optimize import least_squares
d=np.load('parts.npz'); Hob,H2,H4,S2=d['Hob'],d['H2'],d['H4'],d['S2']
w,v=np.linalg.eigh(S2)
Q=v[:,np.abs(w-15/4)<1e-6]; Dd=v[:,np.abs(w-3/4)<1e-6]
def H(Dq,B,C): return Dq*Hob+(49*B+7*C)*H2+(12.6*C)*H4
def clus(vals,tol=3.0):
    vals=np.sort(vals); out=[]; cur=[vals[0]]
    for x in vals[1:]:
        if x-cur[-1]<tol: cur.append(x)
        else: out.append((np.mean(cur),len(cur))); cur=[x]
    out.append((np.mean(cur),len(cur))); return out
def spec(p):
    h=H(*p); return np.linalg.eigvalsh(Q.T@h@Q), np.linalg.eigvalsh(Dd.T@h@Dd)
def show(p):
    g,dd=spec(p); E0=g[0]
    print(np.round(p,1)); print(" Q",[(round(e-E0),m) for e,m in clus(g)]); print(" D",[(round(e-E0),m) for e,m in clus(dd)])
show((2155,600,3000)); show((0,600,0)); show((0,0,3000))
EOF
python3 fit4.py