cd <SANDBOX_TMP>/w && cat > scan.py << 'EOF'
from fit2 import quart_rel, res
import numpy as np
best=None
for Dq in np.arange(500,800,25):
    for B in np.arange(600,1100,50):
        r=res((Dq,B))*100
        s=np.sum(r**2)
        if best is None or s<best[0]: best=(s,Dq,B,r)
print(best)
EOF
python3 scan.py 2>/dev/null | tail -3