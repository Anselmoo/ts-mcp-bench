import numpy as np, hashlib, json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ts import spectrum

def states(t):
    mult = int(t[0]); ir = t[1:-1]
    return mult * {'A1':1,'A2':1,'E':2,'T1':3,'T2':3}[ir]

grid = [0.5*i for i in range(9)]
out = []
for x in grid:
    lv = spectrum(x)
    tot = sum(states(t) for _,t,_ in lv)
    # check: every term accounted for (210 states); levels counted per term
    six = lv[:6]
    print(f"Dq/B={x}: total states accounted = {tot}")
    out.append({"Dq_over_B": x, "levels": [{"term": t, "E_over_B": round(float(E),4)} for E,t,_ in six]})
    print("  ", [(t, round(float(E),3)) for E,t,_ in six])
json.dump(out, open('levels.json','w'), indent=1)

# fine grid for plot
xs = np.linspace(0,4.0,41)
fig, ax = plt.subplots(figsize=(7,8))
cols = {}
cmap = plt.get_cmap('tab20')
for x in xs:
    lv = spectrum(x)
    for E,t,_ in lv[:20]:
        if E > 60: continue
        if t not in cols: cols[t] = cmap(len(cols)%20)
        ax.plot(x, E, 'o', ms=3, color=cols[t])
for t,c in cols.items():
    ax.plot([], [], 'o', color=c, label=t)
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B')
ax.set_title("Tanabe-Sugano diagram, d6 octahedral, C/B = 4.557 (points: levels)")
ax.legend(fontsize=7, ncol=2)
fig.tight_layout(); fig.savefig('diagram.png', dpi=130)
h = hashlib.sha256(open('diagram.png','rb').read()).hexdigest()
print("sha256", h)
