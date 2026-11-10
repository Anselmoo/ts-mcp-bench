cat > scan.py << 'EOF'
import numpy as np
from fit2 import spectra
for Dq in (615,):
  for B in range(700,1101,50):
    q,d=spectra(Dq,B,0); q=q-q[0]
    print(Dq,B,"T2",round(q[3]),"A2",round(q[6]),"T1P",round(q[7]))
EOF
python3 scan.py 2>&1 | grep -v "cf eig"