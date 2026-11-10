
cat << 'EOF' | python3 -
import numpy as np, scipy.special as sp
print([n for n in dir(sp) if 'sph' in n])
EOF
