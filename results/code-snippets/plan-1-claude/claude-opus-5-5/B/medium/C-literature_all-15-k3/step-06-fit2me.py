import numpy as np, itertools
from scipy.optimize import least_squares
M=np.load('mats.npz'); HD,HB,HC,SS=M['HD'],M['HB'],M['HC'],M['SS']
ms=[-2,-1,0,1,2]; so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),7))
ML=np.array([sum(so[o][0] for o in d) for d in dets])
C4=np.exp(1j*np.pi/2*ML)
def levels(Dq,B,C):
    H=Dq*HD-B*HB-C*HC
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,jk,ki->i',v.T,SS,v)
    w=w-w.min(); out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-4*max(1,B): j+=1
        S=(-1+np.sqrt(1+4*s[i]))/2; mult=int(round(2*S+1)); deg=(j-i)//mult
        ch=np.real(np.sum(np.abs(v[:,i:j])**2*C4[:,None]))/mult
        lab={1:{1:'A1',-1:'A2'}.get(round(ch),'?'),2:'E',3:{1:'T1',-1:'T2'}.get(round(ch),'?')}[deg]
        out.append((w[i],f"{mult}{lab}")); i=j
    return out
def pick(Dq,B,C):
    L=levels(Dq,B,C); cnt={}; r={}
    for e,l in L:
        cnt[l]=cnt.get(l,0)+1; r[(l,cnt[l])]=e
    return r
obs={('4T2',1):8480,('4A2',1):16305,('4T1',2):20360,('2T1',2):21001}
def res(p):
    r=pick(*p); return [r[k]-v for k,v in obs.items()]
for l in levels(850,850,3500)[:14]: print(l)
s=least_squares(res,[850,850,3500]); print(s.x, res(s.x))
r=pick(*s.x); print(sorted([(round(v),k) for k,v in r.items()])[:20])
