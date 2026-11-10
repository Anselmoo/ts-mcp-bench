import numpy as np, itertools
from scipy.optimize import least_squares
d=np.load('<SANDBOX_TMP>/lv.npz')
Mcf,M2,M4=d['Mcf'],d['M2'],d['M4']
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
dets=list(itertools.combinations(range(10),7))
Sz=np.array([sum(0.5*orbs[i][1] for i in dd) for dd in dets])
i3=np.where(np.isclose(Sz,1.5))[0]; i1=np.where(np.isclose(Sz,0.5))[0]
Mtot=np.array([sum(orbs[i][0] for i in dd) for dd in dets])
def H(p):
    Dq,B,C=p; F4=12.6*C; F2=49*B+5*F4/9
    return Dq*Mcf+F2*M2+F4*M4
R=np.exp(-1j*np.pi/2*Mtot)
def lev(p):
    Hm=H(p)
    q,vq=np.linalg.eigh(Hm[np.ix_(i3,i3)])
    dl,vd=np.linalg.eigh(Hm[np.ix_(i1,i1)])
    # doublet T1 levels: eigen of Sz=1/2 not in quartet, with C4 char +1 & deg 3
    # Remove quartets by projecting: quartet-containing vectors -> use S^2 via Sz=3/2 lowering is complex; use multiset removal on energies
    dl=list(dl)
    Qe=[]
    for x in q:
        j=int(np.argmin([abs(y-x) for y in dl])); dl.pop(j)
    return q
def qlevels(p):
    q=lev(p)
    g=[]
    for x in q:
        if not g or abs(x-g[-1][0])>1e-2: g.append([x,1])
        else: g[-1][1]+=1
    return g
def doublet_T1(p):
    Hm=H(p)
    w,v=np.linalg.eigh(Hm[np.ix_(i1,i1)])
    # C4 projector classes
    out=[]
    k=0
    while k<len(w):
        j=k
        while j+1<len(w) and abs(w[j+1]-w[k])<1e-2: j+=1
        P=v[:,k:j+1]@v[:,k:j+1].conj().T
        chi=np.trace(P@np.diag(R[i1])).real
        out.append((w[k],j-k+1,round(chi,1)))
        k=j+1
    # remove quartet T1 (+1) and T2 levels: quartets occur within sector; remove by energy match
    qs=lev(p)
    rem=[]
    for e,n,c in out:
        cnt=n
        for x in qs:
            if abs(x-e)<1e-2 and cnt>0: cnt-=1
        if cnt>0: rem.append((e,cnt,c))
    return rem
def res(x, Dq=None):
    p=(Dq if Dq is not None else x[0], x[1], x[2]) if Dq is None else (Dq,x[0],x[1])
    q=qlevels(p); g0=q[0][0]
    Dl=[(e-g0,n,c) for e,n,c in doublet_T1(p) if n==3 and c==1.0]
    return np.array([q[1][0]-g0, q[2][0]-g0, q[3][0]-g0, Dl[1][0]])
obs=np.array([8480,16305,20360,21001])
# Dq fixed by 10Dq = nu1
r=least_squares(lambda x: res(x,Dq=848)[1:]-obs[1:], [900,4000], x_scale=[100,300], bounds=([300,1000],[1500,8000]))
print("Dq fixed 848: B,C=",np.round(r.x,1), "pred:",np.round(res(r.x,Dq=848),0), "resid", np.round(r.fun,1))
r2=least_squares(lambda x: res(x)-obs, [890,915,3800], x_scale=[100,100,300])
print("free fit Dq,B,C=",np.round(r2.x,1),"pred:",np.round(res(r2.x),0),"resid",np.round(r2.fun,1))
