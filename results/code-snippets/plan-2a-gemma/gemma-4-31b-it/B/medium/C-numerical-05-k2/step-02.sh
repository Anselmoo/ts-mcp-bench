cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def calculate_energies(Dq, B):
    Delta_o = 10 * Dq
    E_T2g = 0.6 * Delta_o
    E_A2g = 2.0 * Delta_o
    H = np.array([[-0.4 * Delta_o, 6 * B],
                  [6 * B, 15 * B]])
    eigenvalues = np.linalg.eigvals(H)
    E_T1_low = min(eigenvalues).real
    E_T1_high = max(eigenvalues).real
    
    # T2g, A2g, T1g(P)
    return E_T2g - E_T1_low, E_A2g - E_T1_low, E_T1_high - E_T1_low

def fit_assignment_A(p):
    # nu1=T2g, nu2=T1g(P), nu3=A2g
    Dq, B = p
    nu_T2, nu_A2, nu_T1P = calculate_energies(Dq, B)
    return [nu_T2 - 15730, nu_T1P - 24030, nu_A2 - 32750]

def fit_assignment_B(p):
    # nu1=T2g, nu2=A2g, nu3=T1g(P)
    Dq, B = p
    nu_T2, nu_A2, nu_T1P = calculate_energies(Dq, B)
    return [nu_T2 - 15730, nu_A2 - 24030, nu_T1P - 32750]

# Try solving for A and B
print("Assignment A:")
try:
    # Using first two to guess
    resA = fsolve(lambda p: fit_assignment_A(p)[:2], [1200, 1000])
    print(f"Dq: {resA[0]}, B: {resA[1]}, Nu: {calculate_energies(*resA)}")
except Exception as e:
    print(e)

print("\nAssignment B:")
try:
    resB = fsolve(lambda p: fit_assignment_B(p)[:2], [600, 1000])
    print(f"Dq: {resB[0]}, B: {resB[1]}, Nu: {calculate_energies(*resB)}")
except Exception as e:
    print(e)
EOF
python3 solution.py
