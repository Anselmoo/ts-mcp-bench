cd /; python3 - << 'EOF'
import numpy as np
from scipy.optimize import least_squares
EOF
echo; python3 -c "import scipy; print('ok')"