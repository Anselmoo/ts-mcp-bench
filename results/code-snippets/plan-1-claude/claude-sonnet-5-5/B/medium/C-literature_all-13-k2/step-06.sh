cd <SANDBOX_TMP>; python3 -c "
import a
from a import *
a.U[:]=np.eye(5)
H0=a.H(0,900,3500,3)
e=np.linalg.eigvalsh(H0);print(np.round(e-e.min()))
"