import numpy as np, itertools
from scipy.optimize import least_squares
d=np.load('<SANDBOX_TMP>/lv.npz')
Mcf,M2,M4=d['Mcf'],d['M2'],d['M4']
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
dets=list(itertools.combinations(range(10),7))
Sz=np.array([sum(0.5*orbs[i][1] for i in dd) for dd in dets])
i3=np.where(np.isclose(Sz,1.5))[0]; i1=np.where(np.isclose(Sz,0.5))[0]
def H(p):
    Dq,B,C=p; F4=12.6*C; F2=49*B+5*F4/9
    return Dq*Mcf+F2*M2+F4*M4
def groups(ev,tol=1e-2):
    out=[]
    for x in np.sort(ev):
        if not out or abs(x-out[-1][0])>tol: out.append([x,1])
        else: out[-1][1]+=1
    return out
def spec(p):
    Hm=H(p)
    q=np.linalg.eigvalsh(Hm[np.ix_(i3,i3)])
    dl=list(np.linalg.eigvalsh(Hm[np.ix_(i1,i1)]))
    for x in q:
        j=int(np.argmin([abs(y-x) for y in dl])); dl.pop(j)
    return groups(q), groups(np.array(dl))
def model(p,which):
    qd,dg=spec(p); g0=qd[0][0]
    Tdoub=[e-g0 for e,n in dg if n==3]
    return np.array([qd[1][0]-g0,qd[2][0]-g0,qd[3][0]-g0,Tdoub[which]])
obs=np.array([8480,16305,20360,21001])
# list T doublets near 21001 for a reference
qd,dg=spec((890,915,4000)); g0=qd[0][0]
Tl=[round(e-g0) for e,n in dg if n==3]
print("T-doublet levels (ref):",Tl)
results=[]
for which in range(len(Tl)):
    best=None
    for start in [(900,900,3500),(850,800,4000),(1000,1000,4500),(900,1000,3000)]:
        try:
            r=least_squares(lambda x: model(x,which)-obs,start,x_scale=[100,100,300],bounds=([300,300,1000],[2000,1500,8000]))
            if best is None or r.cost<best.cost: best=r
        except Exception as e: pass
    if best is not None:
        results.append((np.sqrt(np.mean(best.fun**2)),which,best.x,best.fun))
results.sort(key=lambda t:t[0])
for rr in results[:5]:
    print(round(rr[0],1), rr[1], np.round(rr[2],1), np.round(rr[3],1))
