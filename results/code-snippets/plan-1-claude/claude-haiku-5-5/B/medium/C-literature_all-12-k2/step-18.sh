cat > chk.py << 'EOF'
import numpy as np
from fit2 import spectrum
q,dl=spectrum((1e-9,1000,0.0))
print("Dq=0,C=0 quartets rel:", np.round(q-q[0],2))
q,dl=spectrum((0,1000,0.0)); print(np.round(q-q[0],2))
q,dl=spectrum((0,1000,4000.0)); print("C=4000:",np.round(q-q[0],2))
print("doublets rel to quartet ground (B=1000,C=4000,Dq=0):", np.round(np.unique(np.round(dl-q[0],1)),1))
EOF
python3 chk.py