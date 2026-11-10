from ts import *
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,161)
E=[]
for x in xs:
    w=np.linalg.eigvalsh(H2+x*B*H1); u=np.unique(np.round((w-w[0])/B,6)); E.append(u[:30])
n=min(len(e) for e in E)
E=np.array([e[:n] for e in E])
plt.figure(figsize=(7,8))
xs2=np.linspace(0.025,4,160)
# plot quartets/doublets via labeled levels
from collections import defaultdict
pts=defaultdict(list)
for x in xs2:
    L=levels(x); e0=L[0][0]; cnt=defaultdict(int)
    for e,m,d,c,nn in L:
        sym={1:('A1' if c>0 else 'A2'),2:'E',3:('T1' if c>0 else 'T2')}[d]
        k=f"{m}{sym}"; cnt[k]+=1
        pts[(k,cnt[k])].append((x,(e-e0)/B*0+ (e-e0)))
for (k,i),v in pts.items():
    v=np.array(v)
    if len(v)<len(xs2): continue
    plt.plot(v[:,0],v[:,1],'-' if k[0]=='4' else '--',lw=1)
    plt.text(4.02,v[-1,1],f"$^{k[0]}{k[1]}_{{{k[2:]}g}}$" if len(k)>2 else f"$^{k[0]}{k[1]}_g$",fontsize=7)
plt.xlim(0,4.4); plt.ylim(0,80); plt.xlabel('Dq/B'); plt.ylabel('E/B')
plt.title('Tanabe–Sugano d$^3$ (O$_h$), B=828, C=3390 cm$^{-1}$, C/B=%.3f'%(C/B))
plt.savefig('diagram.png',dpi=120)
