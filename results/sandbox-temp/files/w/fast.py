import numpy as np
from ts import *
# linear decomposition: H = Dq*HL + F2*H2 + F4*H4
def build_parts():
    Z = np.zeros((N,N),complex)
    global HL,H2,H4
    # ligand field part
    h1 = hmat(1.0)
    HL = np.zeros((N,N),complex)
    for j,d in enumerate(dets):
        for p in range(norb):
            for q in range(norb):
                if abs(h1[p,q])<1e-14: continue
                r=cdag_c(p,q,d)
                if r is None: continue
                s,nd=r; HL[index[nd],j]+=s*h1[p,q]
    # Coulomb parts: build with V from k=2 and k=4 separately
    def coul(Vfun):
        V=Vfun
        H=np.zeros((N,N),complex)
        for j,d in enumerate(dets):
            for r_ in range(norb):
                a1=c(r_,d)
                if a1 is None: continue
                sg1,o1=a1
                for s_ in range(norb):
                    a2=c(s_,o1)
                    if a2 is None: continue
                    sg2,o2=a2
                    for q in range(norb):
                        a3=cdag(q,o2)
                        if a3 is None: continue
                        sg3,o3=a3
                        for p in range(norb):
                            v=V[p,q,r_,s_]
                            if abs(v)<1e-14: continue
                            a4=cdag(p,o3)
                            if a4 is None: continue
                            sg4,o4=a4
                            H[index[o4],j]+=0.5*sg1*sg2*sg3*sg4*v
        return H
    V2 = Vmat(1.0,0.0); V4 = Vmat(0.0,1.0)
    H2 = coul(V2); H4 = coul(V4)
build_parts()
def H_of(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    return Dq*HL + F2*H2 + F4*H4
def levels_fast(Dq,B,C):
    H=H_of(Dq,B,C); H=0.5*(H+H.conj().T).real
    w,v=np.linalg.eigh(H)
    s2=np.einsum('ij,ik,kj->j',v,S2,v)
    quart=np.array(sorted([wi for wi,s in zip(w,s2) if abs(s-15/4)<1e-5]))
    doub=np.array(sorted([wi for wi,s in zip(w,s2) if abs(s-3/4)<1e-5]))
    return quart,doub
