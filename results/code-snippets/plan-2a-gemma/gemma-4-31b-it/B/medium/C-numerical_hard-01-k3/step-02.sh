cat << 'EOF' > solve_d4.py
import numpy as np
from scipy.optimize import fsolve

def get_energies(Dq, B):
    C = 4.7 * B
    # For d4 LS, ground state is 3T1g.
    # We need the energies of the lowest three spin-allowed excited states.
    # These are 3T2g, 3Eg, and 3T1g(P).
    
    # Using the Tanabe-Sugano approximations for d4 LS:
    # E(3T1g) = -10Dq + repulsion_1
    # E(3T2g) = 0 + repulsion_2
    # E(3Eg) = 0 + repulsion_3
    # E(3T1g_P) = 10Dq + repulsion_4
    
    # This is too complex. Let's use the transition energies.
    # For d4 LS:
    # nu1 (3T1g -> 3T2g) = 10Dq - 3B + something
    # nu2 (3T1g -> 3Eg) = 10Dq - 3B + something
    # nu3 (3T1g -> 3T1g(P)) = 10Dq + 15B + something
    
    # Let's try to fit the given bands: 18850, 19750, 20560.
    # Differences: 900, 810.
    # If nu3 - nu2 = 810, then 15B - (something) = 810.
    # This would mean B is small (~ 50-100).
    # Then nu2 - nu1 = 900.
    # If nu1 and nu2 are 3T2g and 3Eg, they are usually very close.
    # This fits!
    
    return None

EOF
python3 solve_d4.py
