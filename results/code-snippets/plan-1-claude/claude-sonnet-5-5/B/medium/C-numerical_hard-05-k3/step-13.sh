cd <SANDBOX_TMP> && python3 -c "
from a import *
e=spectrum(0,1000,4000,1,1);print(sorted(set(np.round(e))))"