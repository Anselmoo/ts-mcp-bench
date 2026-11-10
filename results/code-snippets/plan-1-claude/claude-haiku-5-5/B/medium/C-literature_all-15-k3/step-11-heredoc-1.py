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
def quart(p):
    Hm=H(p); q=np.linalg.eigvalsh(Hm[np.ix_(i3,i3)]); return groups(q)
def doublets(p):
    Hm=H(p)
    q=np.linalg.eigvalsh(Hm[np.ix_(i3,i3)])
    dl=list(np.linalg.eigvalsh(Hm[np.ix_(i1,i1)]))
    for x in q:
        j=int(np.argmin([abs(y-x) for y in dl])); dl.pop(j)
    return groups(np.array(dl))
def qres(x):
    qd=quart((x[0],x[1],0)); g0=qd[0][0]
    e=[qd[1][0]-g0,qd[2][0]-g0,qd[3][0]-g0]
    return np.array(e)-np.array([8480,16305,20360])
r=least_squares(qres,[900,900],x_scale=[100,100])
print("quartet LSQ Dq,B:",np.round(r.x,1),"resid",np.round(r.fun,1))
Dq,B=r.x
print("quartet levels:",[(round(e,1),n) for e,n in [(x[0]-quart((Dq,B,0))[0][0],x[1]) for x in quart((Dq,B,0))]])
# doublets for C scan
for C in [3000,3500,4000,4500,5000]:
    dg=doublets((Dq,B,C)); g0=quart((Dq,B,C))[0][0]
    print(C,[(round(e-g0),n) for e,n in dg if n==3][:8])
