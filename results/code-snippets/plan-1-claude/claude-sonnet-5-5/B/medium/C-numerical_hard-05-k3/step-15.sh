cd <SANDBOX_TMP> && python3 - <<'E'
from a import *
import a
# two-electron: direct test of 3P-3F etc with F2=1,F4=0 vs
for B,C in [(1,0),(0,1)]:
  e=spectrum(0,B,C,1,1); print(B,C,sorted(set(np.round(e,4))))
E