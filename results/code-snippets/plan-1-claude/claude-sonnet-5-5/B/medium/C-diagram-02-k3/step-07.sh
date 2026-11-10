cat > p.py <<'E'
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from t import levels
xs=np.linspace(0,4,81);Y=[]
for x in xs:
    r=levels(max(x,1e-7));g=r[0][0];Y.append([e-g for e,_,_ in r[:12]])
Y=np.array(Y)
for k in range(12): plt.plot(xs,Y[:,k],lw=1)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d4 Tanabe-Sugano, C/B=%.3f'%(3902/814));plt.ylim(0,60)
plt.savefig('diagram.png',dpi=120)
E
python3 p.py 2>&1 | grep -v Matplotlib; realpath diagram.png; sha256sum diagram.png