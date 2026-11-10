import numpy as np, itertools
from scipy.optimize import least_squares
from run2 import classify
obs=np.array([19240.,21890.,23000.])
def dist(p):
    out=classify(*p)
    e=np.array([x[0] for x in out])
    vals=[]
    for x in sorted(e):
        if vals and abs(x-vals[-1][0])<1e-7: vals[-1][1]+=1
        else: vals.append([x,1])
    return vals
sols=[]
rng=np.random.default_rng(1)
for trial in range(40):
    p0=np.array([rng.uniform(600,1000), rng.uniform(600,1100), 0])
    p0[2]=rng.uniform(3,5)*p0[1]
    # scan over assignments using current spectrum
    vals=dist(p0)
    Ts=[i for i,(e,m) in enumerate(vals) if m==3 and e>1e-6]
    Es=[i for i,(e,m) in enumerate(vals) if m==2 and e>1e-6]
    for a,b in itertools.permutations(Ts,2):
        for c in Es:
            def res(p):
                v=dist(p)
                # positions of same indices
                try:
                    return np.array([v[a][0],v[b][0],v[c][0]])-obs
                except IndexError: return np.ones(3)*1e6
            r=least_squares(res,p0,bounds=([0,100,200],[5000,3000,15000]),xtol=1e-10,ftol=1e-10)
            if np.max(np.abs(r.fun))<5:
                sols.append((a,b,c,tuple(np.round(r.x,1)),np.round(r.fun,2)))
seen=set()
for s in sols:
    key=(s[0],s[1],s[2],tuple(np.round(s[3],-1)))
    if key in seen: continue
    seen.add(key); print(s)
