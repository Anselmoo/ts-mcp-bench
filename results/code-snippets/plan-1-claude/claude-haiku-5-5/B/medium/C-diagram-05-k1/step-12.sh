export MPLCONFIGDIR=$PWD/.mpl; mkdir -p $MPLCONFIGDIR; cat > plot.py << 'EOF'
import numpy as np, main, hashlib
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
xs = np.round(np.arange(0,4.0001,0.1),3)
rows=[]
for x in xs:
    out,_ = main.levels_for(x)
    lv=[]
    for sec,mult in (('q',4),('d',2)):
        for E,g,Lf,_ in out[sec]:
            lv.append((E, f"{mult}{ {'A1':'A1g','A2':'A2g','E':'Eg','T1':'T1g','T2':'T2g'}[g]}", mult))
    E0 = min(t[0] for t in lv)
    rows.append([(e-E0, lab, m) for e,lab,m in lv])
fig,ax = plt.subplots(figsize=(7,6))
cols = {'4':'tab:red','2':'tab:blue'}
for x,row in zip(xs,rows):
    for e,lab,m in row:
        ax.scatter(x, e, s=8, color=cols[str(m)])
# legend proxies
ax.scatter([],[],color='tab:red',label='quartet'); ax.scatter([],[],color='tab:blue',label='doublet')
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B'); ax.set_title('Tanabe-Sugano d7 octahedral (C/B = 4.26)')
ax.set_xlim(0,4); ax.set_ylim(0,70); ax.legend()
fig.savefig('diagram.png', dpi=120)
h = hashlib.sha256(open('diagram.png','rb').read()).hexdigest()
print('sha256', h)
EOF
python3 plot.py 2>&1 | grep -v '^{' ; ls -la diagram.png; sha256sum diagram.png; pwd