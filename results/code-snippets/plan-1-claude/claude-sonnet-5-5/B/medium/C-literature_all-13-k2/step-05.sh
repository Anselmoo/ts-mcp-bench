cd <SANDBOX_TMP>; python3 -c "
from a import *
H0=H(0,900,3500,3);print(abs(H0-H0.conj().T).max())
e=np.linalg.eigvalsh(H0);print(np.round(e-e.min()))
print(C[2].round(3))
"