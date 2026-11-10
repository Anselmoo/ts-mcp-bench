cat > plot.py << 'EOF'
import numpy as np, hashlib, os
os.environ.setdefault("MPLCONFIGDIR","/tmp/mpl")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ts
xs=np.round(np.arange(0,4.0001,0.1),3)
data={}
for x in xs:
    lv=ts.levels(x*ts.B); E0=lv[0][0]
    for E,m,nm in lv:
        data.setdefault(f"{m}{nm}g",[]).append((x,(E-E0)/ts.B))
fig,ax=plt.subplots(figsize=(7,8))
for lab,pts in data.items():
    p=np.array(pts)
    ax.plot(p[:,0],p[:,1],'.',ms=3,label=lab)
ax.set_xlim(0,4); ax.set_ylim(0,60)
ax.set_xlabel("Dq/B"); ax.set_ylabel("E/B")
ax.set_title("Tanabe-Sugano diagram d5 octahedral (C/B=4.43)")
ax.legend(ncol=2,fontsize=7,markerscale=3)
fig.savefig("../diagram.png",dpi=120)
print(hashlib.sha256(open("../diagram.png","rb").read()).hexdigest())
EOF
python3 plot.py 2>&1 | grep -v -i matplotlib; ls -la ..; pwd