cat > plot.py << 'EOF'
from run_d6 import *
import hashlib, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
dqs=np.round(np.arange(0,4.0001,0.1),3)
data=[]
for dq in dqs:
    lv=levels(float(dq)); e0=lv[0][0]
    data.append((dq,[(float(e-e0),2*S+1,n) for e,S,n in lv]))
fig,ax=plt.subplots(figsize=(7,8))
cols={'T2':'C0','E':'C1','T1':'C2','A1':'C3','A2':'C4'}
seen=set()
for dq,lv in data:
    for E,mult,n in lv:
        if E>60: continue
        lab=f"{mult}{n}g" if False else None
        key=(mult,n)
        c=cols[n]
        ax.plot(dq,E,'.',ms=3,color=c if mult!=1 else ('k' if mult==1 else c))
ax.set_xlabel("Dq/B"); ax.set_ylabel("E/B")
ax.set_title("Tanabe-Sugano diagram d6 octahedral, C/B=4.557 (all levels)")
from matplotlib.lines import Line2D
h=[Line2D([0],[0],marker='o',ls='',color=c,label=k) for k,c in cols.items()]
ax.legend(handles=h,title="irrep (black: ignore)",loc='upper left',fontsize=7)
fig.savefig("diagram.png",dpi=130)
import os
print(os.path.abspath("diagram.png"))
print(hashlib.sha256(open("diagram.png","rb").read()).hexdigest())
EOF
python3 plot.py 2>&1 | grep -v -i matplotlib | tail -3