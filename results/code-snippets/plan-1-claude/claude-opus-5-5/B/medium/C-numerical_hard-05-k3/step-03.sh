mkdir -p /tmp/w && cat > /tmp/w/d6.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache
EOF
python3 -c "import sympy" 2>&1