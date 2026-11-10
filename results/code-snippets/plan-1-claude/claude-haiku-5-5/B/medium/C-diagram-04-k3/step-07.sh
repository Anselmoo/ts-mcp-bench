cat > plot_d6.py << 'EOF'
import sys, json
sys.argv = ['x', '6']
exec(open('ts.py').read())
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
grid = np.round(np.arange(0, 4.01, 0.1), 2)
xs, ys, ss = [], [], []
for Dq in grid:
    lv = analyze(Dq)
    E0 = lv[0][0]
    for e, S, nm in lv:
        xs.append(Dq); ys.append(e-E0); ss.append(int(round(S)))
fig, ax = plt.subplots(figsize=(7, 8))
cols = {0: 'tab:blue', 1: 'tab:green', 2: 'tab:red'}
for S in (0, 1, 2):
    m = [i for i, s in enumerate(ss) if s == S]
    ax.scatter([xs[i] for i in m], [ys[i] for i in m], s=6, c=cols[S], label=f'S={S}')
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B')
ax.set_title('Tanabe-Sugano diagram, d6 octahedral, C/B = 4.557 (spin-free)')
ax.set_xlim(0, 4); ax.set_ylim(0, 80)
ax.legend()
fig.savefig('diagram.png', dpi=130)
print('saved')
EOF
time python3 plot_d6.py 2>/dev/null && sha256sum diagram.png && pwd