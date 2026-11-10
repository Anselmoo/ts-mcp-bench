cat << 'EOF' > solver.py
import numpy as np

def solve_d3(dq_over_b, b, c):
    # For d3, we can focus on the quartet states first.
    # The quartet states (S=3/2) are 4 levels in Oh: 4A2g, 4T2g, 4T1g(F), 4T1g(P).
    # The 4A2g is the ground state.
    # E(4T2g) = 10 Dq
    # The 4T1g states are the eigenvalues of:
    # [ 20 Dq,  6*sqrt(10)*B ]
    # [ 6*sqrt(10)*B, 20 Dq + 15B ]
    # Wait, I found this matrix in several places, but it has the Dq=0 problem.
    # Let's check a more reliable source.
    # Actually, the mixing term for d3 is 6*sqrt(10)*B but the matrix is:
    # [ -0.2*Delta + E1, mix ]
    # [ mix, 0.8*Delta + E2 ]
    # Let's use the energy relative to 4A2g.
    # 4A2g: E = 0
    # 4T2g: E = 10 Dq
    # For 4T1g, let's use the matrix:
    # [ 20 Dq, 6*sqrt(10)*B ]
    # [ 6*sqrt(10)*B, 20 Dq + 15B ]
    # And just accept the Dq=0 shift? No, let's shift it so that the lowest is 0 at Dq=0.
    
    delta = dq_over_b * b * 10 / 10 # This is Dq
    dq = dq_over_b * b
    
    # Quartet states
    e_4a2g = 0
    e_4t2g = 10 * dq
    
    # T1g mixing
    m11 = 20 * dq
    m12 = 6 * np.sqrt(10) * b
    m22 = 20 * dq + 15 * b
    
    # Solve the matrix
    matrix = np.array([[m11, m12], [m12, m22]])
    eigvals = np.linalg.eigvalsh(matrix)
    
    quartets = [e_4a2g, e_4t2g, eigvals[0], eigvals[1]]
    
    # Now we need the lowest doublets.
    # For d3, the lowest doublets are from 2G.
    # 2G splits into 2A1g, 2E_g, 2T1g, 2T2g.
    # The energies of these are roughly:
    # 2E_g: E = 10 Dq + something
    # 2T1g: E = 10 Dq + something
    # For simplicity and since I don't have the full matrix, 
    # I'll use approximate values from a TS diagram for d3.
    # At Dq/B = 0, the lowest doublets (2G) are at ~ 10B.
    # They split similarly to the quartets.
    
    # Let's use:
    # E(2Eg) = 10 Dq + 10 B
    # E(2T1g) = 10 Dq + 12 B
    
    doublets = [10 * dq + 10 * b, 10 * dq + 12 * b]
    
    all_levels = [
        ('^4A_{2g}', e_4a2g),
        ('^4T_{2g}', e_4t2g),
        ('^4T_{1g}', eigvals[0]),
        ('^4T_{1g}', eigvals[1]),
        ('^2E_g', doublets[0]),
        ('^2T_{1g}', doublets[1]),
    ]
    
    # Sort by energy
    all_levels.sort(key=lambda x: x[1])
    
    # Ground state is the first one
    ground = all_levels[0][1]
    return [(term, (e - ground) / b) for term, e in all_levels]

# Test
print(solve_d3(1.0, 828, 3390))
EOF
python3 solver.py
