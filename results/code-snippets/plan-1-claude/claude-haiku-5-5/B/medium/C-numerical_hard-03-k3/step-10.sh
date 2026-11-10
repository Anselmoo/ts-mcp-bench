cd <SANDBOX_TMP> && cat << 'EOF' > run3.py
import sys; sys.path.insert(0,'<SANDBOX_TMP>')
from run2 import doublets
import numpy as np
for x in [1.5,2.0,2.5,3.0,3.5]:
    E=doublets(x)
    print(x, np.round(E-E[0],3)[:8])
EOF
python3 run3.py 2>&1 | grep -v "^11 \|cwd"