cd /dev/shm && cat > run.py <<'EOF'
from sym import *
from scipy.linalg import null_space
from scipy.spatial.transform import Rotation as Rot
Vs=null_space(S2m)
print('singlet dim',Vs.shape[1])
# classify group elements
cls=[]
for R in Og:
    rv=Rot.from_matrix(R).as_rotvec(); th=np.linalg.norm(rv)
    if th<1e-9: c='E'
    elif abs(th-2*np.pi/3)<1e-6: c='C3'
    elif abs(th-np.pi/2)<1e-6: c='C4'
    elif abs(th-np.pi)<1e-6:
        n=np.abs(rv/th)
        c='C2' if np.sum(n>0.5)==1 else "C2p"
    cls.append(c)
from collections import Counter
print(Counter(cls))
chars={
 'A1':{'E':1,'C4':1,'C2':1,'C3':1,'C2p':1},
 'A2':{'E':1,'C4':-1,'C2':1,'C3':1,'C2p':-1},
 'E': {'E':2,'C4':0,'C2':2,'C3':-1,'C2p':0},
 'T1':{'E':3,'C4':1,'C2':-1,'C3':0,'C2p':-1},
 'T2':{'E':3,'C4':-1,'C2':-1,'C3':0,'C2p':1},
}
Lams=[Lam(R) for R in Og]
def irrep_proj(name):
    P=np.zeros((210,210),complex)
    d=chars[name]['E']
    for R,c,L_ in zip(Og,cls,Lams):
        P+=chars[name][c]*L_
    return d/24*P
Pr={k:irrep_proj(k) for k in chars}
Pss={k:Vs.conj().T@Pr[k]@Vs for k in chars}
def analyze(Dq,B,C=None,verbose=True):
    if C is None: C=4*B
    H=build(Dq,B,C)
    Hs=Vs.conj().T@H@Vs
    w,U=np.linalg.eigh(Hs)
    # cluster
    clusters=[]; i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-6: j+=1
        Ucl=U[:,i:j+1]
        mult={k:np.real(np.trace(Ucl.conj().T@Pss[k]@Ucl)) for k in chars}
        clusters.append((w[i],{k:round(v,3) for k,v in mult.items() if abs(v)>1e-6}))
        i=j+1
    return clusters
if __name__=="__main__":
    cl=analyze(2.0,1.0)
    for e,m in cl: print(round(e,4),m)
EOF
python3 run.py