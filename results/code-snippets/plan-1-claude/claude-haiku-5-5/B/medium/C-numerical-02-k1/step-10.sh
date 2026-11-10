python3 - << 'EOF'
import re
s=open('run.py').read()
s=s.replace("""    H=Hmat(Dq,F0,F2,F4).real
    w,v=np.linalg.eigh(H)
    S=np.real(np.einsum('in,ij,jn->n',v,S2op,v))
    return w,S""","""    H=Hmat(Dq,F0,F2,F4).real
    w,v=np.linalg.eigh(H+50.0*S2op)
    S=np.real(np.einsum('in,ij,jn->n',v,S2op,v))
    E=np.real(np.einsum('in,ij,jn->n',v,H,v))
    return E,S""")
open('run.py','w').write(s)
EOF
python3 -c "
from run import *
import collections
w,S=levels(0,0,1.0,0.0)
print(collections.Counter(np.round(S,3)))
q=sorted([round(e,5) for e,s in zip(w,S) if abs(s-3.75)<1e-3]); print(collections.Counter(q))
w,S=levels(0,0,0.0,1.0)
print(collections.Counter(np.round(S,3)))
q=sorted([round(e,5) for e,s in zip(w,S) if abs(s-3.75)<1e-3]); print(collections.Counter(q))
"