cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def get_d3_energies(Dq, B):
    # Energies for d3 quartet states relative to the 4F barycenter
    # E(4A2g) = 6 Dq
    # E(4T2g) = -6 Dq
    # E(4T1g) are the eigenvalues of:
    # [[-Dq, 6*sqrt(10)*Dq*B], [6*sqrt(10)*Dq*B, 15*B - Dq]] 
    # Wait, the coupling term is 6*sqrt(10)*B*Dq? No.
    # The correct coupling is 6*sqrt(10)*Dq*B is not dimensionally correct.
    # Let's use the standard Tanabe-Sugano energy formulas.
    
    # For d3 (standard):
    # E(4A2g) = 0
    # E(4T2g) = 10*Dq
    # E(4T1g) are roots of:
    # x^2 - x(15*B + 10*Dq) + (10*Dq)(15*B + 10*Dq) - 360*B*Dq^2 / B? No.
    
    # Let's use the most reliable formulas for d3:
    # E(4A2g) = 0
    # E(4T2g) = 10*Dq
    # E(4T1g_F) = 15*B + 10*Dq - sqrt((15*B - 10*Dq)**2 + 120*Dq**2) # No, that's not it.
    pass

# Let's use the d7 high spin approximate formulas first to get a starting point
# nu1 = Delta - 4*B
# nu2 = 2*Delta - B
# nu3 = 2*Delta + 15*B
# nu1 = 6150, nu2 = 12400, nu3 = 16850
EOF
python3 -c "
nu1, nu2, nu3 = 6150, 12400, 16850
# Using nu3 - nu2 = 16*B
B = (nu3 - nu2) / 16
Delta = (nu2 + B) / 2
print(f'Approx Dq: {Delta/10:.2f}, B: {B:.2f}, nu1_calc: {Delta - 4*B:.2f}')
"
