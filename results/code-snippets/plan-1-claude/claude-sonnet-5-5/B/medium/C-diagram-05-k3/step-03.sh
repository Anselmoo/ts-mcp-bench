python3 -c "
import pickle,matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt,numpy as np
from a import lv
xs=np.linspace(0,4,81);Y=[[e for e,k in lv(x)[:10]] for x in xs]
plt.plot(xs,Y);plt.xlabel('Dq/B');plt.ylabel('E/B');plt.savefig('diagram.png')
" >/dev/null; readlink -f diagram.png; sha256sum diagram.png