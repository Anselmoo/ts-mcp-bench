
cd /tmp/tsbench-run-bifa9lgd && sed -i 's/from scipy.special import sph_harm/from scipy.special import sph_harm_y/; s/def Y(l,m): return sph_harm(m,l,PH,TH)/def Y(l,m): return sph_harm_y(l,m,TH,PH)/' d4lib.py && cat << 'EOF' > fit.py
import numpy as np, d4lib as L
from scipy.optimize import least_squares
M_ee_cache={}
F2_EE=None
def ee(F2,F4): return L.ee_ops(F2,F4)
# precompute ee for unit F2 and unit F4 (linear)
E2=L.ee_ops(1.0,0.0); E4=L.ee_ops(0.0,1.0)
def spectrum(Dq,B,C=None,ratio=4.7):
    C=ratio*B
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=F2*E2+F4*E4+L.oneel(L.cf_matrix(Dq))
    H=(H+H.conj().T)/2
    w,v=np.linalg.eigh(H)
    # total spin S from S^2 operator: use Sz-resolved count: number of unpaired electrons via spin ladder
    return w,v
# Spin of each determinant: total Sz=0 for 4 electrons? need S=1 states: Sz=1 subspace (2 up-spin extra)
# Build S^2 in determinant basis
def S2op():
    import itertools
    Sz=np.zeros((len(L.dets),)*2)
    Sp=np.zeros((len(L.dets),)*2,complex)
    Sp_m=np.zeros((len(L.dets),)*2,complex)
    for j,dj in enumerate(L.dets):
        for m in range(5):
            up=m*2; dn=m*2+1
            # S+ = sum c+_up c_dn
            if dn in dj and up not in dj:
                st,s1=L.ann(dj,dn); st,s2=L.cre(st,up)
                Sp[L.idx[st],j]+=s1*s2
    Sm=Sp.conj().T
    Sz_=np.zeros(len(L.dets))
    for j,dj in enumerate(L.dets):
        Sz_[j]=sum(0.5 if (x%2==0) else -0.5 for x in dj)
    S2=Sm@Sp+np.diag(Sz_)**2+ (Sp*0)
    S2=Sm@Sp+np.diag(Sz_*(Sz_))+np.diag(Sz_)
    return S2
S2=S2op()
def states(Dq,B):
    H=L.oneel(L.cf_matrix(Dq))
    C=4.7*B; F4=441*C/35; F2=(441*B+5*F4)/9
    H=H+F2*E2+F4*E4
    H=(H+H.conj().T)/2
    # diagonalize in S^2 blocks: project
    w,v=np.linalg.eigh(H+100*S2)  # shift S2 penalty to separate spins
    out=[]
    for i in range(len(w)):
        s2=np.real(v[:,i].conj()@S2@v[:,i])
        out.append((w[i],s2))
    return out
if __name__=='__main__':
    res=states(2000,800)
    for e,s2 in sorted(res)[:20]:
        print(round(e,1), round(s2,3))
EOF
python3 fit.py