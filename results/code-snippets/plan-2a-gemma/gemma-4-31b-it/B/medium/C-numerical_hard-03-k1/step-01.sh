cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def calculate_energies(Dq, B, C):
    # Using standard formulas for d5 low spin octahedral
    # Ground state: 2T2g
    # Excited states from t2g^4 eg^1: 2T1g, 2T2g
    # Excited states from t2g^3 eg^2: 2T1g, 2T2g, 2A1g
    
    # Let's use the results from a reliable source for d5 LS
    # Transition 1: 2T2g -> 2T1g (t2g^4 eg^1)
    # Transition 2: 2T2g -> 2T2g (t2g^4 eg^1)
    # Transition 3: 2T2g -> 2T1g (t2g^3 eg^2)
    
    # However, I need the exact expressions for the energies.
    # Let's use the expressions for the energies of d5 LS terms:
    # The ground state is 2T2g.
    # The configuration t2g^4 eg^1 gives 2T1g and 2T2g.
    # The configuration t2g^3 eg^2 gives 2T1g and 2A1g (and maybe others).
    
    # Energy of 2T2g (ground): E0
    # Energy of 2T1g (t2g^4 eg^1): 10Dq + f1(B, C)
    # Energy of 2T2g (t2g^4 eg^1): 10Dq + f2(B, C)
    # Energy of 2T1g (t2g^3 eg^2): 20Dq + f3(B, C)
    
    # Let me find the f functions.
    # For d5 low spin:
    # E(2T2g ground) = -10Dq + 15B - 1.5C (approx)
    # This is getting complicated. Let's find a simpler way.
    pass

EOF
python3 solver.py
