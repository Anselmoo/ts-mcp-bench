import numpy as np, run2, hashlib
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict
# energies at 9 grid points with full precision
for Dq in np.arange(0,4.01,0.5):
    L = run2.levels_at(Dq); E0=L[0][0]
    print(f"Dq={Dq:.1f}", [(f"{2*S+1}{G}g", round(e-E0,4)) for e,S,G in L[:6]])
# fine grid for plot, per (S,G) sector ranked
grid = np.linspace(0,4,81)
curves = defaultdict(list)
for Dq in grid:
    L = run2.levels_at(Dq); E0=L[0][0]
    per = defaultdict(list)
    for e,S,G in L: per[(S,G)].append(e-E0)
    for k,v in per.items():
        for r,e in enumerate(sorted(v)):
            curves[(k,r)].append((Dq,e))
fig,ax = plt.subplots(figsize=(7,8))
for (k,r),pts in curves.items():
    S,G = k
    if min(p[1] for p in pts) > 60: continue
    x,y = zip(*pts)
    col = {0:'tab:green',1:'tab:blue',2:'tab:red'}[S]
    ax.plot(x,y,color=col,lw=1.2)
    ax.text(x[-1], y[-1], f"{2*S+1}{G}g", fontsize=7, color=col)
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B'); ax.set_xlim(0,4.4); ax.set_ylim(0,60)
ax.set_title('Tanabe-Sugano diagram d4 octahedral, C/B=4.794 (singlets green, triplets blue, quintets red)')
fig.savefig('diagram.png', dpi=120)
print(hashlib.sha256(open('diagram.png','rb').read()).hexdigest())
