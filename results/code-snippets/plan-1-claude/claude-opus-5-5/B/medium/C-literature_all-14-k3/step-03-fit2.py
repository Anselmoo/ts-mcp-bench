import numpy as np, itertools
from scipy.optimize import least_squares
M=np.load('mats.npz')
ms=range(-2,3); orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
dets=list(itertools.combinations(range(10),7))
C4=np.diag([1j**(sum(orbs[p][0] for p in D)%4) for D in dets])
def lev(Dq,B,C):
    F4=C/35; F2=B+5*F4
    H=49*F2*M['H2']+441*F4*M['H4']+Dq*M['HD']
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        P=v[:,i:j]
        S=np.trace(P.T@M['S2']@P).real/(j-i)
        mult=round((-1+np.sqrt(1+4*S)))+1
        ch=np.trace(P.conj().T@C4@P).real/mult
        lab={(3,1):'T1',(3,-1):'T2',(2,0):'E',(1,1):'A1',(1,-1):'A2'}[((j-i)//mult,round(ch))]
        out.append((w[i]-w[0],str(mult)+lab)); i=j
    return out
def pick(L,lab,k): return [e for e,l in L if l==lab][k-1]
def res(p):
    L=lev(*p)
    return [pick(L,'4T2',1)-8100,pick(L,'4T1',2)-19400,pick(L,'2T1',2)-21600]
for C0 in (3000,4000,5000):
  r=least_squares(res,[900,950,C0]); print(r.x,r.fun)
print(lev(*r.x)[:14])
