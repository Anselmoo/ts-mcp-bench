cd <SANDBOX_TMP> && python3 -c "
from a import *
print(levels(900,3200,0)[:8])
print(np.abs(H1-H1.conj().T).max(),np.abs(H2-H2.conj().T).max())
print(levels(900,3200,1000)[:3])
"