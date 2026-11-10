cat > plot.py << 'EOF'
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import run
xs=np.arange(0,4.001,0.1)
data=[]
for x in xs:
    lv=run(x); E0=lv[0][0]
    data.append([(e-E0) for e,l in lv[:12]])
    labels=[l for e,l in lv[:12]]
fig,ax=plt.subplots(figsize=(7,8))
nlev=12
for k in range(nlev):
    ys=[d[k] if len(d)>k else np.nan for d in data]
    ax.plot(xs,ys,'k-',lw=1)
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B')
ax.set_title('Tanabe-Sugano diagram d3 (octahedral), C/B=%.3f'%(3390/828))
ax.set_ylim(0,60); ax.set_xlim(0,4)
fig.savefig('diagram.png',dpi=120)
print("saved")
EOF
python3 plot.py 2>&1 | tail -1 && sha256sum diagram.png && pwd