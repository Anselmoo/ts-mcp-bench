cat > plot.py <<'E'
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ts import *
xs=np.linspace(0.02,4,50);ys=[]
for x in xs:
    L=levels(x*B);e0=L[0][0];ys.append([(t,(e-e0)/B) for e,t in L[:8]])
for x in [0.02,4]: pass
fig=plt.figure(figsize=(7,6))
for k in range(8):
    plt.plot(xs,[y[k][1] for y in ys],'-',lw=1)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d4 Oh, B=814, C=3902');plt.ylim(0,45)
plt.savefig('diagram.png',dpi=120)
H=H2;w=np.linalg.eigvalsh(H);print(sorted(set(np.round((w-w.min())/B,4)))[:4])
E
python3 plot.py 2>&1 | grep -v matplotlib; sha256sum diagram.png; realpath diagram.png