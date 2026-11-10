cat > test2.py << 'EOF'
import numpy as np
from ff import build_V
from fock import hamiltonian
h0=np.zeros((10,10))
F2,F4=1.0,0.625
V=build_V({0:0.0,2:F2,4:F4})
H,b=hamiltonian(2,h0,V)
ev=np.linalg.eigvalsh(H)
vals,counts=np.unique(np.round(ev,6),return_counts=True)
for v,c in zip(vals,counts): print(v,c)
np.save('d2ev.npy',ev)
EOF
python3 test2.py