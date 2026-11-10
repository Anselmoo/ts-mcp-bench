cd <SANDBOX_TMP> && python3 -c "
from a import *
print(levels(900,3200,100)[:8])
print(levels(900,3200,500)[:8])
print(levels(0,0,1000)[:8])
print(np.trace(H1).real/N)"