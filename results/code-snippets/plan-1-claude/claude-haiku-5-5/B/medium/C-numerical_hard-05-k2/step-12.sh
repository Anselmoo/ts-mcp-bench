cat > fit.py <<'EOF'
import numpy as np, itertools
from d6 import *
B=1.0; C=4.5
h1,V=build(B,C,1.0)
h0,_=build(B,C,0.0)
Hcf_1=h1-h0            # one-body cubic-field part per Dq
basis,Hee,S2=ops(h0,V)
_,Hcf,_=ops(Hcf_1,np.zeros((10,10,10,10)))
Lz=np.array([sum(m*(((s>>orb(m,0))&1)+((s>>orb(m,1))&1)) for m in ms) for s in basis],float)
C4=np.diag(np.exp(-1j*np.pi/2*Lz))
def spectrum(x):
    H=Hee+x*Hcf
    w,U=np.linalg.eigh(H+1000*S2)
    s2=np.einsum('ij,ik,kj->j',U,S2,U)  # diag of U^T S2 U... careful
    s2=np.real(np.diag(U.T@S2@U))
    sel=np.abs(s2)<1e-6
    Us=U[:,sel]; Hs=Us.T@H@Us; ws,Vs=np.linalg.eigh(Hs)
    Ss=Us@Vs
    # group degenerate levels
    levels=[]; i=0
    while i<len(ws):
        j=i
        while j+1<len(ws) and abs(ws[j+1]-ws[i])<1e-6: j+=1
        P=Ss[:,i:j+1]
        chi=np.trace(P.conj().T@C4@P).real
        levels.append((ws[i],j-i+1,round(chi,3)))
        i=j+1
    return levels
if __name__=="__main__":
    for x in [0,1,2,3]:
        print('x=',x)
        for L in spectrum(x)[:8]: print('  E=%.4f deg=%d chi(C4)=%s'%L)
EOF
python3 fit.py