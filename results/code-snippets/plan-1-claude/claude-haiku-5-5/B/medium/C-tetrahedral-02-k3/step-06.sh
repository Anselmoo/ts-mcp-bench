
cd /tmp/tsbench-run-la9r0a6w && sed -i 's/H=np.zeros((N,N))/H=np.zeros((N,N),dtype=complex)/' d3.py && cat << 'EOF' > fit.py
from d3 import *
from scipy.optimize import least_squares
def levels(Dq_t,B):
    # d7 tet = d3 oct with D = -Dq_t ; B=1 unit: F2=49B
    H=build(49*B,0.0,-Dq_t)
    e=np.linalg.eigvalsh(H)
    return np.sort(e)
# zero-field check
print(np.round(levels(0,1),4))
# Dq_t=1,B=0 check -> 10Dq
print(np.round(levels(1,0),4))
EOF
python3 fit.py