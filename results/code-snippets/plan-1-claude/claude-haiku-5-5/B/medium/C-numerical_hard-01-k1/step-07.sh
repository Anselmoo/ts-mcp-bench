python3 - <<'EOF'
import re
s=open('d4.py').read()
s=s.replace("from scipy.special import sph_harm\n","from scipy.special import sph_harm_y\n")
s=s.replace("    return sph_harm(q, k, ph, np.arccos(ct))","    return sph_harm_y(k, q, np.arccos(ct), ph)")
open('d4.py','w').write(s)
EOF
python3 -c "
import d4,numpy as np
st,H,S2=d4.build(0.0)
print(H.shape, np.allclose(H,H.T), np.allclose(S2,S2.T))
ev,evec=np.linalg.eigh(H)
Sv = np.einsum('ij,ik,kj->j', evec, S2, evec)
import collections
d=collections.defaultdict(list)
for e,s in zip(ev,Sv): d[round(s,3)].append(round(e,4))
for s in d: print('S(S+1)=',s, sorted(set(d[s])))
"