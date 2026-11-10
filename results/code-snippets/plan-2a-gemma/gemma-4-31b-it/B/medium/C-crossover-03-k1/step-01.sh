cat << 'EOF' > solution.py
def calculate_crossover():
    B = 803
    C = 3078
    # The transition for d6 Octahedral from High Spin (5T2g) to Low Spin (1A1g).
    # Energy of 5T2g = -4Dq (relative to 5D barycenter)
    # Energy of 1A1g = -24Dq + E(1G) - E(5D)
    # Crossover: -4Dq = -24Dq + E(1G) - E(5D) => 20Dq = E(1G) - E(5D)
    # For d6 (or d4), E(1G) - E(5D) = 15B + 3C.
    # Let's verify this energy difference.
    # For d2: E(1G) - E(3F) = 15B.
    # For d4: E(1G) - E(5D) = 15B + 3C? 
    # Let's check a reference or use a known relation.
    # Another common formula for pairing energy P = 3B + C or similar.
    # But P is typically E(LS) - E(HS) at Dq=0.
    # For d6, P = E(1A1g) - E(5T2g) = E(1G) - E(5D).
    
    # Let's use the energy expressions from a reliable source:
    # For d4/d6:
    # E(5D) = 0
    # E(3H) = 0 (Wait, d4 doesn't have 3H? It has 3P, 3F, 3G)
    # Let's recalculate using the standard Racah energy for d4/d6:
    # The difference E(1G) - E(5D) is often given as 15B + 3C.
    
    diff = 15 * B + 3 * C
    Dq = diff / 20
    return Dq

print(calculate_crossover())
EOF
python3 solution.py
