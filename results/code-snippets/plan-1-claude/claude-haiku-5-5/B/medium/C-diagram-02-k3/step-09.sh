ls && MPLCONFIGDIR=/tmp/mpl python3 -c "
import pickle, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fine = pickle.load(open('fine.pkl','rb'))
xs=sorted(fine)
fig,ax=plt.subplots(figsize=(7,8))
from collections import defaultdict
tracks=defaultdict(list)
for x in xs:
    for k,(lab,E) in enumerate(fine[x]):
        if E<60: tracks[(lab,k)].append((x,E))
for (lab,k),pts in tracks.items():
    ax.scatter([p[0] for p in pts],[p[1] for p in pts],s=3,c='k')
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B'); ax.set_title('d4 octahedral Tanabe-Sugano diagram (C/B=4.79), sorted-level tracks')
ax.set_xlim(0,4); ax.set_ylim(0,60)
fig.savefig('diagram.png',dpi=120)
" && sha256sum diagram.png && ls -la diagram.png