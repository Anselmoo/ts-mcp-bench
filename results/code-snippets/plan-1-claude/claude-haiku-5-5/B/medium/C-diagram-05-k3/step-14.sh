cd <SANDBOX_TMP>/ts && cat > plot.py << 'EOF'
exec(open('final.py').read().split('table = {}')[0])
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, hashlib, os
dqs = np.arange(0,4.0001,0.05)
data = {}
for dq in dqs:
    L = levels_at(dq) if dq>0 else l0s
    for e,n in L: data.setdefault(n,[]).append((dq,e))
fig, ax = plt.subplots(figsize=(8,10))
for n,pts in data.items():
    x,y = zip(*pts)
    y=np.array(y)
    m = y<=70
    ax.plot(np.array(x)[m], y[m], lw=1.2)
    if m.any():
        i = np.where(m)[0][-1]
        ax.text(x[i]+0.02, y[i], n, fontsize=6)
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B')
ax.set_title('Tanabe-Sugano diagram, octahedral d7, C/B = 4.26 (B=859, C=3660 cm-1)')
ax.set_xlim(0,4.6); ax.set_ylim(0,70)
fig.tight_layout()
out = os.path.join(os.getcwd(),'diagram.png')
fig.savefig(out, dpi=130)
print(out, hashlib.sha256(open(out,'rb').read()).hexdigest())
EOF
python3 plot.py 2>&1 | tail -1; ls -la <SANDBOX_TMP>/ts/diagram.png 2>/dev/null