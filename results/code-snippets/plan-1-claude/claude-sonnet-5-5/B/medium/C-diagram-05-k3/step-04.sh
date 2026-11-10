export MPLCONFIGDIR=/tmp/m; python3 -c "
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt,numpy as np
from a import lv
xs=[];Y=[]
for x in np.linspace(0.013,4,80):
    try: Y.append([e for e,k in lv(x)[:10]]);xs.append(x)
    except Exception: pass
plt.plot(xs,Y);plt.xlabel('Dq/B');plt.ylabel('E/B');plt.savefig('diagram.png')
" >/dev/null 2>&1; readlink -f diagram.png; sha256sum diagram.png