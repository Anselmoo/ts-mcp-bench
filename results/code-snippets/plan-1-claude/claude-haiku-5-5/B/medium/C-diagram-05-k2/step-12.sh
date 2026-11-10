cat > plot.py << 'EOF'
from ts import *
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, hashlib
xs=np.arange(0,4.0001,0.1)
data={}
for x in xs:
    lv=levels(x); E0=lv[0][0]
    # group by label, sorted by energy within label (no crossings within same symmetry)
    groups={}
    for E,S,g in lv: groups.setdefault(lab(S,g),[]).append(E-E0)
    for k,vals in groups.items():
        data.setdefault(k,[]).append((x,sorted(vals)))
fig,ax=plt.subplots(figsize=(7,8))
for k,pts in data.items():
    nmax=max(len(v) for _,v in pts)
    for j in range(nmax):
        xx=[x for x,v in pts if len(v)>j]; yy=[v[j] for x,v in pts if len(v)>j]
        ax.plot(xx,yy,'k-' if k.startswith('4') else 'k--',lw=0.9)
    xx=[x for x,v in pts]; ax.plot([],[],label=k)
ax.set_xlim(0,4); ax.set_ylim(0,70)
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B')
ax.set_title('Tanabe-Sugano diagram, d7 octahedral, C/B=%.3f'%(Cr))
ax.legend(fontsize=7,ncol=2)
fig.savefig('diagram.png',dpi=150)
print(hashlib.sha256(open('diagram.png','rb').read()).hexdigest())
EOF
<B_VENV>/bin/python3 plot.py 2>&1 | tail -3; ls -la diagram.png; pwd