from sym import *
from scipy.optimize import brentq
Vs=null_space(S2m)
cls=[]
for R in Og:
    rv=Rot.from_matrix(R).as_rotvec(); th=np.linalg.norm(rv)
    if th<1e-9: c='E'
    elif abs(th-2*np.pi/3)<1e-6: c='C3'
    elif abs(th-np.pi/2)<1e-6: c='C4'
    else:
        n=np.abs(rv/th)
        c='C2' if np.sum(n>0.5)==1 else "C2p"
    cls.append(c)
chars={'A1':{'E':1,'C4':1,'C2':1,'C3':1,'C2p':1},'A2':{'E':1,'C4':-1,'C2':1,'C3':1,'C2p':-1},
 'E': {'E':2,'C4':0,'C2':2,'C3':-1,'C2p':0},'T1':{'E':3,'C4':1,'C2':-1,'C3':0,'C2p':-1},
 'T2':{'E':3,'C4':-1,'C2':-1,'C3':0,'C2p':1}}
Lams=[Lam(R) for R in Og]
Pss={}
for k in chars:
    P=sum(chars[k][c]*L_ for c,L_ in zip(cls,Lams))*chars[k]['E']/24
    Pss[k]=Vs.conj().T@P@Vs
def levels(Dq,B,C=None):
    if C is None: C=4*B
    H=build(Dq,B,C)
    Hs=Vs.conj().T@H@Vs
    w,U=np.linalg.eigh(Hs)
    out=[]; i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-6: j+=1
        Ucl=U[:,i:j+1]
        mult={k:round(float(np.real(np.trace(Ucl.conj().T@Pss[k]@Ucl))),3) for k in chars}
        out.append((w[i],{k:v for k,v in mult.items() if abs(v)>1e-6}))
        i=j+1
    return out
def Tstates(x):
    # B=1, C=4 ; returns list of (energy relative to ground, label), T states only
    lv=levels(x,1.0)
    g0=lv[0][0]
    res=[]
    for e,m in lv[1:]:
        for k in m:
            if k in ('T1','T2'): res.append((e-g0,k))
    return res
if __name__=="__main__":
    # sanity ground
    print(levels(2.0,1.0)[0])
    for x in [2.0,2.2,2.25,2.3]:
        T=Tstates(x)
        print(x,[(round(e,3),k) for e,k in T[:5]])
    # target
    r2=26330/16700; r3=35020/16700
    # Solve x such that E(T2a)/E(T1a)=r2
    f=lambda x: [e for e,k in Tstates(x) if k=='T2'][0]/[e for e,k in Tstates(x) if k=='T1'][0]-r2
    x2=brentq(f,2.0,2.5,xtol=1e-6)
    T=Tstates(x2)
    E1=T[0][0]
    print('x=Dq/B (fit on band1,2):',x2)
    print('lowest levels (B=1):',[(round(e,4),k) for e,k in T[:5]])
    print('ratios to E1:',[round(e/E1,4) for e,k in T[:5]])
