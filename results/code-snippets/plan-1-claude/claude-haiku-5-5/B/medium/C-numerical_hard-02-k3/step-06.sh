cat > /dev/null << 'EOF'
EOF
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
exec(open('/dev/null').read())
EOF
echo