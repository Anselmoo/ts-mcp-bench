import numpy as np, itertools
from scipy.optimize import least_squares
d=np.load('<SANDBOX_TMP>/lv.npz')
Mcf,M2,M4=d['Mcf'],d['M2'],d['M4']
print("trace M2,M4:",np.trace(M2),np.trace(M4))
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
dets=list(itertools.combinations(range(10),7))
Sz=np.array([sum(0.5*orbs[i][1] for i in dd) for dd in dets])
Mtot=np.array([sum(orbs[i][0] for i in dd) for dd in dets])
i3=np.where(np.isclose(Sz,1.5))[0]; i1=np.where(np.isclose(Sz,0.5))[0]
def H(p):
    Dq,B,C=p; F4=12.6*C; F2=49*B+5*F4/9
    return Dq*Mcf+F2*M2+F4*M4
R=np.exp(-1j*np.pi/2*Mtot)
def classify(p):
    Hm=H(p)
    out={}
    for name,ii in [('Q',i3),('D',i1)]:
        w,v=np.linalg.eigh(Hm[np.ix_(ii,ii)])
        # group
        groups=[]; k=0
        while k<len(w):
            j=k
            while j+1<len(w) and abs(w[j+1]-w[k])<1e-2: j+=1
            vecs=v[:,k:j+1]
            P=vecs@vecs.conj().T
            chi=np.trace(P@np.diag(R[ii]))
            groups.append((w[k],j-k+1,np.round(chi.real,2)))
            k=j+1
        out[name]=groups
    return out
out=classify((890,915,4000))
print("quartets (E, deg, chi C4):")
for e,n,c in out['Q']: print(round(e,1),n,c)
print("doublets (E, deg, chi C4):")
for e,n,c in out['D']: print(round(e,1),n,c)
