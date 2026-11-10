cd /tmp && cat > chk.py <<'EOF'
exec(open('/dev/stdin').read()) if False else None
EOF
python3 - <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
# quick check of Gaunt-based angular factors: <Y20 Y20|1/r12|Y20 Y20> reduction
ms=[-2,-1,0,1,2]
def Ang(mi,mk,K,q):
    if -mi+mk-q!=0 or abs(q)>K: return 0.0
    return (-1)**(mi)*((-1)**q)*float(gaunt(2,2,K,-mi,mk,-q))
# Check: for K=0, angular a = int |Y_mi|^2 * Y00^*... should equal 1/sqrt(4pi) * delta
print([round(Ang(m,m,0,0),5) for m in ms], 1/np.sqrt(4*np.pi))
# Check F0 Slater: F0 = sum over K=0 coefficient for d-orbital pair (0,0),(0,0): should be 4pi*(1/(4pi))^2 ... = 1/(4pi) *4pi =1
print(4*np.pi*Ang(0,0,0,0)**2)
EOF