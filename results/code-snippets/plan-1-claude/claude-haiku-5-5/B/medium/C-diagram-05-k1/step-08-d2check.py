import numpy as np, itertools
import ts
def run(Nel, F2, F4):
    basis = sorted([sum(1<<i for i in c) for c in itertools.combinations(range(10),Nel)])
    idx={b:i for i,b in enumerate(basis)}
    g = ts.angular()
    Vo = F2*g[2]+F4*g[4]
    terms=[]
    for a,b,c,d in itertools.product(range(10),repeat=4):
        if (a%2)!=(c%2) or (b%2)!=(d%2): continue
        v=Vo[a//2,b//2,c//2,d//2]
        if abs(v)>1e-12: terms.append((a,b,c,d,v))
    H=np.zeros((len(basis),)*2)
    for j,bj in enumerate(basis):
        for a,b,c,d,v in terms:
            s1,b1=ts.ann(c,bj)
            if not s1: continue
            s2,b2=ts.ann(d,b1)
            if not s2: continue
            s3,b3=ts.cre(b,b2)
            if not s3: continue
            s4,b4=ts.cre(a,b3)
            if not s4: continue
            H[idx[b4],j]+=0.5*v*s1*s2*s3*s4
    # M_S=1 sector for d2 (both up): n_up=2, n_dn=0 -> triplets only; use M_S=0 sector
    sec=[i for i,b in enumerate(basis) if sum((b>>p)&1 for p in range(0,10,2))==Nel//2+ (Nel%2)*0 and True]
    up=[i for i,b in enumerate(basis) if sum((b>>p)&1 for p in range(0,10,2))==1 and sum((b>>p)&1 for p in range(1,10,2))==1]
    Hs=H[np.ix_(up,up)]
    return np.round(np.linalg.eigvalsh(Hs),6)
for F2,F4 in ((1,0),(0,1)):
    print(F2,F4, run(2,F2,F4))
