cat << 'EOF' > check_nu3.py
import numpy as np

B = 304.25
Dq = 901.0
E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
E_T1g_P_un = 15*B
trace = E_T1g_F_un + E_T1g_P_un
det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
disc = np.sqrt(trace**2 - 4*det)
print(f'nu3: {disc}')
EOF
python3 check_nu3.py
