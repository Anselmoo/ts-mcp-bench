import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import ts_calc as T
xs = np.arange(0, 4.001, 0.1)
fig, ax = plt.subplots(figsize=(7,6))
col = {'5':'tab:red','3':'tab:blue','1':'tab:green'}
for x in xs:
    L = T.levels(x)
    E0 = L[0][0]
    for e, t, _ in L:
        ax.plot(x, e-E0, '.', color=col[t[0]], ms=3)
for s,c in col.items():
    ax.plot([], [], 'o', color=c, label=f'spin multiplicity {s}')
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B (relative to ground level)')
ax.set_title('Tanabe-Sugano diagram, d4 octahedral, C/B = 4.79 (B=814, C=3902 cm$^{-1}$)')
ax.legend(); ax.set_ylim(-2, 60)
fig.savefig('diagram.png', dpi=150)
