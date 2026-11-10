import numpy as np
from ts import idx, SO, N
import itertools
d=np.load('mats.npz'); Hcf,H2,H4,S2=d['Hcf'],d['H2'],d['H4'],d['S2']
D=list(itertools.combinations(range(N),7))
# C4z rotation phases on determinants: exp(-i*pi/2*m) per occupied spin-orbital
R=np.array([np.prod([np.exp(-1j*np.pi/2*SO[i][0]) for i in occ]) for occ in D])
def levels(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    H=Dq*Hcf+F2*H2+F4*H4
    w,v=np.linalg.eigh(H+1000*S2)
    s2=np.einsum('ia,ij,ja->a',v.conj(),S2,v).real
    res=[]
    # group by energy and S
    i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-6 and abs(s2[j+1]-s2[i])<1e-6: j+=1
        V=v[:,i:j+1]
        E=w[i:j+1].mean()-1000*s2[i]
        # C4 character: trace of V^dag R V
        chi=np.trace(V.conj().T@(R[:,None]*V))
        res.append((round(s2[i],2),E,j-i+1,np.round(chi,3)))
        i=j+1
    return res
if __name__=='__main__':
    import sys
    Dq,B,C=map(float,sys.argv[1:4])
    for r in levels(Dq,B,C):
        if r[0]>0.7 and r[0]<4: print(r[0], round(r[1],1), r[2], r[3])
