
cat << 'EOF' | python3 -
import numpy as np
exec(open('/dev/null').read())
EOF
echo; cat << 'EOF' | python3 -
import numpy as np
from math import *
# Analytic check of free-ion d8 Racah: E(3F)=-7B-? ; relative levels expected: 3P:+15B, 1G:+(... )
# Using Racah: E(1D)=9B+... we just print raw spectrum from scratch next call
EOF
