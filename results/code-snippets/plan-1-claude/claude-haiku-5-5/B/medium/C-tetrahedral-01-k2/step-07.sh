cd <SANDBOX_TMP>/w && cat << 'EOF' > fit.py
import numpy as np
from d7 import *
from scipy.optimize import brentq, least_squares
F={0:0.0,2:1.0,4:0.625}
Vee=np.load('Vee.npy')
H0,basis=hamiltonian(F,0.0,Vee)   # Coulomb only (Dq=0)
# one-body part: H(Dq)-H0 is linear in Dq: compute with Dq=1 and subtract
H1,_=hamiltonian(F,1.0,np.zeros_like(Vee))
H0=H0.real; H1=H1.real
np.save('H0.npy',H0); np.save('H1.npy',H1)
B=0.1998/15.0
def levels(Dq_over_B):
    H=H0+Dq_over_B*B*H1
    ev=np.sort(np.linalg.eigvalsh(H))
    return ev
ev=levels(0.0); print('free', ev)
# B from 4P-4F
def spectrum(x, Bv):
    ev=np.sort(np.linalg.eigvalsh(H0*Bv/B + x*Bv*H1))
    return ev
for x in [0.5,1.0,1.5]:
    print(x, np.round(spectrum(x,1.0)-spectrum(x,1.0)[0],4))
EOF
python3 fit.py