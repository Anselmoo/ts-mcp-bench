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
def spec(p):
    Hm=H(p)
    q=np.linalg.eigvalsh(Hm[np.ix_(i3,i3)])
    dl=list(np.linalg.eigvalsh(Hm[np.ix_(i1,i1)]))
    for x in q:
        j=int(np.argmin([abs(y-x) for y in dl])); dl.pop(j)
    # quartet distinct
    qd=[];
    for x in np.sort(q):
        if not qd or abs(x-qd[-1][0])>1e-3: qd.append([x,1])
        else: qd[-1][1]+=1
    dd=np.sort(np.array(dl))
    dg=[];
    for x in dd:
        if not dg or abs(x-dg[-1][0])>1e-3: dg.append([x,1])
        else: dg[-1][1]+=1
    return qd,dg
# grid
best=[]
obs=[8480,16305,20360]
for Dq in np.arange(600,1101,25):
  for B in np.arange(600,1101,25):
    for C in np.arange(2400,5201,200):
        qd,dg=spec((Dq,B,C))
        g0=qd[0][0]
        e=[qd[1][0]-g0, qd[2][0]-g0, qd[3][0]-g0]
        r=np.sqrt(np.mean((np.array(e)-np.array(obs))**2))
        best.append((r,Dq,B,C,e))
best.sort(key=lambda t:t[0])
for b in best[:8]: print(np.round(b[0],1), b[1:4], np.round(b[4],0))
