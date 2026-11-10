sed -i 's/np.arange(0,4.01,0.5)/np.arange(0,4.01,0.1)/; s/^    print(Dqb.*$//' t.py && cat >> t.py <<'E'
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict
xs=sorted(res)
fig,ax=plt.subplots(figsize=(7,8))
for k,x in enumerate(xs):
    for e,t,d in res[x][:12]:
        ax.plot([x],[(e-res[x][0][0])/B],'.',color={'1':'b','3':'g','5':'r'}[t[0]],ms=3)
ax.set_xlabel('Dq/B');ax.set_ylabel('E/B');ax.set_title('d6 Tanabe-Sugano (B=551, C=2511); r=quintet g=triplet b=singlet')
ax.set_ylim(0,70)
plt.savefig('diagram.png',dpi=120)
E
python3 t.py 2>&1 | grep -v cache; sha256sum diagram.png; pwd