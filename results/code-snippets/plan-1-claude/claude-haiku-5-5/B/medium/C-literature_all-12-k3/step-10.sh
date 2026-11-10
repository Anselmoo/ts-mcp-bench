cd <SANDBOX_TMP>/w && python3 -c "
from ts import *
h=hmat(1000); print(np.round(np.linalg.eigvalsh(h),3))
H=build_H(1000,0,0); H=H.real; w,v=np.linalg.eigh(H); print(np.unique(np.round(w,1)))
"