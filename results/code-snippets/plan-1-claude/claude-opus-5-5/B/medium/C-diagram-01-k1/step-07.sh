export MPLCONFIGDIR=$PWD/.mpl; python3 -c "
from ts import *
import numpy as np
print(np.allclose(S2,S2.T)); w=np.linalg.eigvalsh(S2); print(sorted(set(np.round(w,4))))
print(np.allclose(S2@H2,H2@S2), np.allclose(S2@H1,H1@S2))
"