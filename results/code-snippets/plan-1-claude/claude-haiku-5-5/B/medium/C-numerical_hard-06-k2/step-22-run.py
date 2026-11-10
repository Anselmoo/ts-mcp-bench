from sym import *
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
chars={
 'A1':{'E':1,'C4':1,'C2':1,'C3':1,'C2p':1},
 'A2':{'E':1,'C4':-1,'C2':1,'C3':1,'C2p':-1},
 'E': {'E':2,'C4':0,'C2':2,'C3':-1,'C2p':0},
 'T1':{'E':3,'C4':1,'C2':-1,'C3':0,'C2p':-1},
 'T2':{'E':3,'C4':-1,'C2':-1,'C3':0,'C2p':1},
}
Lams=[Lam(R) for R in Og]
Pr={}
for k in chars:
    P=sum(chars[k][c]*L_ for c,L_ in zip(cls,Lams))
    Pr[k]=chars[k]['E']/24*P
Pss={k:Vs.conj().T@Pr[k]@Vs for k in chars}
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
def bands(x):
    # B=1, C=4, Dq=x
    lv=levels(x,1.0)
    g0=lv[0][0]
    ex=[(e-g0,m) for e,m in lv[1:]]
    T=[(e,list(m.keys())[0]) for e,m in ex if 'T' in list(m.keys())[0]]
    return T
if __name__=="__main__":
    import sys
    for x in [1.0,1.5,2.0,2.5,3.0]:
        T=bands(x)[:4]
        print(x, [(round(e,3),s) for e,s in T])
        E1=T[0][0]
        print('   ratios E2/E1', round(T[1][0]/E1,4), 'E3/E1', round(T[2][0]/E1,4), 'ground-state A1 check', levels(x,1.0)[0][1])
