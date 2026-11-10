import numpy as np, itertools
from scipy.optimize import least_squares
from fast import levels
obs=np.array([19240.,21890.,23000.])
def lv(p): 
    return levels(*p)
rng=np.random.default_rng(2)
found=[]
for trial in range(60):
    p0=np.array([rng.uniform(500,1500), rng.uniform(500,1000), 0.]); p0[2]=rng.uniform(3,5)*p0[1]
    vals=lv(p0)
    T=[i for i,(e,m) in enumerate(vals) if m==3 and e>1]
    E=[i for i,(e,m) in enumerate(vals) if m==2 and e>1]
    for a,b in itertools.permutations(T,2):
        for c in E:
            def res(p):
                v=lv(p)
                if max(a,b,c)>=len(v): return np.ones(3)*1e5
                return np.array([v[a][0],v[b][0],v[c][0]])-obs
            try:
                r=least_squares(res,p0,bounds=([100,100,200],[4000,2000,10000]),xtol=1e-12,ftol=1e-12,gtol=1e-12)
            except Exception as ex: continue
            if np.max(np.abs(r.fun))<2:
                found.append((a,b,c,np.round(r.x,1),np.round(r.fun,3)))
uniq={}
for f in found:
    k=(f[0],f[1],f[2],tuple(np.round(f[3],-0)))
    uniq[k]=f
for k,f in uniq.items(): print(f)
