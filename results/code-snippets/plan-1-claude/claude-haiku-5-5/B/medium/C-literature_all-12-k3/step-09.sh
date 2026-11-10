cd <SANDBOX_TMP>/w && python3 -c "
from ts import *
q,d=levels(0,1000,4000); print(np.unique(np.round(q-q[0],1)))
q,d=levels(1000,0,0); print(np.unique(np.round(q-q[0],1)))
"