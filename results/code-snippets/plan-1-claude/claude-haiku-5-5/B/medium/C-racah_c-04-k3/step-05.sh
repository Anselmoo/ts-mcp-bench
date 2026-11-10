cd /tmp/tsbench-run-y2n0otgx 2>/dev/null && touch t && echo ok; python3 - << 'EOF'
import numpy as np
from sympy.physics.wigner import gaunt
print(float(gaunt(2,2,2,0,0,0)))
EOF