cat > run.py << 'EOF'
import numpy as np
from scipy.optimize import brentq
H1=np.load("H1.npy"); H2=np.load("H2.npy"); S2=np.load("S2.npy")
H1=np.real_if_close(H1)
print("H1 imag max", np.abs(np.imag(H1)).max())
H1=np.real(H1)
mu=1e5
def levels(Dq):
    H = Dq*H1 + H2
    ev, vec = np.linalg.eigh(H + mu*S2)
    out={}
    for v in vec.T:
        S2v = v@S2@v
        S = (-1+np.sqrt(1+4*S2v))/2
        S=round(S*2)/2
        E = v@H@v
        out.setdefault(S,[]).append(E)
    return {k:min(v) for k,v in out.items()}
# free-ion check at Dq=0
L=levels(0.0)
print("free-ion lowest per S (cm-1 rel):", {k:round(v-levels(0.0)[2.5],1) for k,v in L.items()})
for Dq in [0,500,1000,1500,2000,2500,3000]:
    L=levels(Dq); print(Dq, {k:round(v,1) for k,v in L.items()})
f=lambda Dq: levels(Dq)[0.5]-levels(Dq)[2.5]
Dqc=brentq(f,500,3000,xtol=1e-6)
print("crossover Dq =",Dqc, " Dq/B=",Dqc/621, " C/B=",2851/621)
EOF
python3 run.py