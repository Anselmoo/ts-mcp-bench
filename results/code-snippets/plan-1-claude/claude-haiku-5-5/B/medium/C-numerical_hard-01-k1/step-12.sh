cat > fit2.py <<'EOF'
import numpy as np
from scan import triplet_levels
obs = np.array([18850,19750,20560.])
xs = np.arange(1.0,5.0,0.01)
data = {x:triplet_levels(x) for x in xs}
np.save('dummy.npy',np.zeros(1))
res=[]
for x in xs:
    lev=data[x]
    E=np.array([a-lev[0][0] for a,m in lev]); deg=[m for a,m in lev]
    for combo in [(1,2,3),(1,2,4),(1,3,4),(2,3,4),(1,2,5),(1,3,5),(2,3,5),(1,4,5)]:
        f=E[list(combo)]
        B=(f@obs)/(f@f)
        r=np.sqrt(np.mean((B*f-obs)**2))
        res.append((round(r,2),round(x,2),combo,round(B,1),tuple(deg[i] for i in combo)))
res.sort()
for r in res[:20]: print(r)
EOF
python3 fit2.py 2>/dev/null | tail -20