
cat << 'EOF' > dbg2.py
import numpy as np
exec(open('fit.py').read().split('if __name__')[0])
H=49*600*O2+ 7*2400*O2 + 63*2400/5*O4
e,v=np.linalg.eigh(H)
from collections import Counter
print(Counter(np.round(e,0)).most_common(20))
# S2 for each eigvector
s2=np.array([x@S2full@x for x in v.T])
print(np.round(s2[:5],3))
# check commutation of H with S2 and with Lz-like? check commutator with S2
print("comm S2,H", np.abs(S2full@H-H@S2full).max())
EOF
python3 dbg2.py 2>&1 | tail -8
