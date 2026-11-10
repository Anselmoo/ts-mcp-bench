cat << 'EOF' > d4_calc.py
import numpy as np

def solve_d4(Dq, B, C):
    # We only need the triplet states.
    # The ground state is 3T1g.
    # We are looking for the three lowest triplet excited states.
    # This is hard to do without the full matrices.
    # Let's use the d2 matrices and shift them for the LS d4 case.
    # For d4 LS, the energy levels are essentially the same as d2
    # but shifted by 10Dq and some B, C terms.
    pass
EOF
python3 d4_calc.py
