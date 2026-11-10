cat > d.py <<'E'
import t, itertools, numpy as np
from t import *
# d2 test by rebuilding with N electrons
def spec(n):
    ds=list(itertools.combinations(range(10),n));ix={d:i for i,d in enumerate(ds)}
    H=np.zeros((len(ds),len(ds)))
    for d in ds:
        j=ix[d]
        for (p,q,r,s),val in G.items():
            x=ann(d,r)
            if not x: continue
            x2=ann(x[1],s)
            if not x2: continue
            y=cre(x2[1],q)
            if not y: continue
            y2=cre(y[1],p)
            if not y2: continue
            H[ix[y2[1]],j]+=0.5*val*x[0]*x2[0]*y[0]*y2[0]
    w=np.linalg.eigvalsh(H);return (w-w[0])/B
print(np.round(spec(2),2)[:12])
E
python3 d.py