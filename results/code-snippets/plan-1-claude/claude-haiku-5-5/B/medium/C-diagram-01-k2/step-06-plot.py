import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, hashlib
import ts
xs=np.arange(0,4.0001,0.1)
fig,ax=plt.subplots(figsize=(7,6))
labels_seen=set()
cmap=plt.get_cmap('tab20')
colors={}
for x in xs:
    terms=ts.analyze(x*ts.B)
    E0=min(t[2] for t in terms)
    for m,n,e,_ in terms:
        lab=f"{ts.sup[m]}{ts.sub[n]}g"
        if lab not in colors: colors[lab]=cmap(len(colors)%20)
        ax.scatter(x,(e-E0)/ts.B,s=12,color=colors[lab],label=lab if lab not in labels_seen else None)
        labels_seen.add(lab)
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B')
ax.set_title(f'Tanabe–Sugano diagram, d³ octahedral, C/B={ts.C/ts.B:.3f}')
ax.set_ylim(-2,60); ax.set_xlim(0,4)
ax.legend(fontsize=7,ncol=2,markerscale=2)
fig.tight_layout(); fig.savefig('diagram.png',dpi=120)
print(hashlib.sha256(open('diagram.png','rb').read()).hexdigest())
