cat << 'EOF' > fast.py
from run import *
from scipy.optimize import least_squares
import time
t=time.time()
Hd=Hmat(1.0,0,0,0).real
H2=Hmat(0,0,1.0,0).real-0
H4=Hmat(0,0,0,1.0).real
print("built",time.time()-t, np.abs(Hd).max(), np.abs(H2).max(), np.abs(H4).max())
np.savez('mats.npz',Hd=Hd,H2=H2,H4=H4,S2=S2op)
EOF
timeout 500 python3 fast.py