python3 -c "
import numpy as np, itertools
import d6
from d6 import *
d6.basis6=lambda: [sum(1<<i for i in c) for c in itertools.combinations(range(10),2)]
F={0:0.0,2:1.0,4:0.0}
V=np.zeros((10,10,10,10))
for a,b,c,d in itertools.product(range(10),repeat=4):
    ma,sa=divmod(a,2); mb,sb=divmod(b,2); mc,sc=divmod(c,2); md,sd=divmod(d,2)
    if sa!=sc or sb!=sd: continue
    V[a,b,c,d]=Vint(ma-2,mb-2,mc-2,md-2,F)
b,H,S2=ops(np.zeros((10,10)),V)
# expected trace: sum over unordered pairs {a,b} of <ab|V|ab> - <ab|V|ba>
tr=0
for a,b_ in itertools.combinations(range(10),2):
    tr+=V[a,b_,a,b_]-V[a,b_,b_,a]
print('trace code',np.trace(H),'expected',tr)
# Also: direct Coulomb matrix element for 3d shell via Gaunt: <m m'|V|m m'> for same spin
"