import numpy as np
from ligf import *
from scipy.optimize import least_squares
# precompute linear pieces: H = Dq*A + F2*P2 + F4*P4
def ops():
    Peg=np.zeros((5,5)); Peg[2,2]=1
    v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2)
    Peg+=np.outer(v,v)
    Vm=-4*np.eye(5)+10*Peg
    A=np.zeros((dim,dim))
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            if s1==s2 and abs(Vm[m1+2,m2+2])>1e-14: A+=Vm[m1+2,m2+2]*cre[i]@ann[j]
    P={0:np.zeros((dim,dim)),2:np.zeros((dim,dim)),4:np.zeros((dim,dim))}
    for k in (2,4):
        F=[0,0,0]; F[k//2]=1.0
        F=tuple(F)
        for i,(m1,s1) in enumerate(orbs):
            for j,(m2,s2) in enumerate(orbs):
                for kk,(m3,s3) in enumerate(orbs):
                    if s1!=s3: continue
                    for l,(m4,s4) in enumerate(orbs):
                        if s2!=s4 or i==j or kk==l: continue
                        val=Vsp(m1,m2,m3,m4,F)
                        if abs(val)<1e-12: continue
                        P[k]+=0.5*val*(cre[i]@cre[j]@ann[l]@ann[kk])
    return A,P[2],P[4]
A,P2,P4=ops()
Mz=np.array([sum(orbs[i][0] for i in range(n) if (st>>i)&1) for st in idx],dtype=float)
C4=np.exp(-1j*np.pi/2*Mz)
def build_fast(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5.0
    H=(Dq*A+F2*P2+F4*P4)[np.ix_(idx,idx)]
    w0,U0=np.linalg.eigh(H+1000.0*S2s)
    ss=np.real(np.einsum('ia,ij,ja->a',U0,S2s,U0))
    S=np.round((-1+np.sqrt(1+4*ss))/2*2)/2
    w=np.real(np.einsum('ia,ij,ja->a',U0,H,U0))
    return w,U0,S
def levels(Dq,B,C):
    w,U0,S=build_fast(Dq,B,C)
    E0=w[np.isclose(S,2.5)].min()
    sel=np.where(np.isclose(S,1.5))[0]
    order=sel[np.argsort(w[sel])]
    groups=[]
    for a in order:
        if groups and abs(w[a]-w[groups[-1][0]])<1e-3*max(1,abs(w[a])): groups[-1].append(a)
        else: groups.append([a])
    info=[]
    for g in groups:
        V=U0[:,g]
        c4=np.real(np.trace(V.conj().T@(C4[:,None]*V)))/4
        c2=np.real(np.trace(V.conj().T@((C4**2)[:,None]*V)))/4
        info.append((w[g[0]]-E0, len(g)//4, round(c4,3), round(c2,3)))
    return info
