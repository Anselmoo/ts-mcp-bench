cat << 'EOF' > calc_energy.py
import numpy as np

def get_energy_d6_hs(Dq):
    # HS ground state: ^5T2
    # Configuration: t2g^4 eg^2
    # Energy relative to barycenter of ^5D free ion:
    # LFSE = 4*(-4Dq) + 2*(6Dq) = -16Dq + 12Dq = -4Dq
    return -4 * Dq

def get_energy_d6_ls(Dq, B, C):
    # LS ground state: ^1A1
    # Configuration: t2g^6 eg^0
    # LFSE = 6*(-4Dq) = -24Dq
    # The repulsion energy of t2g^6 relative to the ^5D free ion state
    # For d^6, the energy of the ^1A1 state (descending from ^1I) relative to ^5D is:
    # E(^1I) - E(^5D) = 15B + 5C (This is a known value for the free ion term)
    # Let's double check this.
    return -24 * Dq + 15 * B + 5 * C

# Check transition:
B = 803
C = 3078
# -4*Dq = -24*Dq + 15*B + 5*C
# 20*Dq = 15*B + 5*C
Dq_crit = (15 * B + 5 * C) / 20
print(f"{Dq_crit=}")
EOF
python3 calc_energy.py
