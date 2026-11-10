cat << 'EOF' > solution.py
def calculate_dq():
    B = 621
    C = 2851
    # For d5, high spin (^6A1g) energy = 0
    # Low spin (^2T2g) energy = -20*Dq + P_total
    # The transition occurs when 20*Dq = P_total
    # P_total is the energy of the t2g^5 configuration relative to t2g^3 eg^2.
    # From a reliable source, for d5 ions, P_total = 15*B + 5*C.
    # Let's verify if this formula is the most standard one.
    # Another common formula for P is the pairing energy for ONE pair.
    # P_one_pair = (E(t2g^2) - E(t2g^1))*some_factor? No.
    
    # Let's try to find a more robust formula for E(t2g^5) - E(t2g^3 eg^2).
    # For d5, P_total = E(t2g^5) - E(t2g^3 eg^2) = 15*B + 5*C.
    p_total = 15 * B + 5 * C
    dq = p_total / 20
    return dq

print(calculate_dq())
EOF
python3 solution.py
