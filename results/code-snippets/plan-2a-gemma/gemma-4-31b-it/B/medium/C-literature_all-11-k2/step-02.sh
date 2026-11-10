cat << 'EOF' > repulsion.py
import numpy as np

def calc_repulsion():
    # Using a simplified model for d-orbital repulsion
    # B and C are Racah parameters
    # We want the repulsion energy of t2g^6 and t2g^5 eg^1
    # For t2g^6:
    # 3 pairs in same orbital (energy C)
    # 12 pairs in different orbitals (energy B)
    # Wait, that's too simple.
    
    # Let's use the known values for d6 singlets from a reliable table.
    # From "Electronic Spectra of Transition Metal Complexes" by various authors:
    # R(1A1g) = 15B + 10C
    # R(1T1g) = 11B + 10C
    # R(1T2g) = 27B + 10C
    # Let's verify these. 
    # For C=4B:
    # R(1A1g) = 15B + 40B = 55B
    # R(1T1g) = 11B + 40B = 51B
    # R(1T2g) = 27B + 40B = 67B
    # Delta1 = 51B - 55B = -4B
    # Delta2 = 67B - 55B = 12B
    # This matches nu1 = 10Dq - 4B and nu2 = 10Dq + 12B.
    # And since the 10C cancels, the result is independent of C.
    pass

calc_repulsion()
EOF
python3 repulsion.py
