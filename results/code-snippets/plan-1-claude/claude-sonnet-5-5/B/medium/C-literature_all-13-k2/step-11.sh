cd <SANDBOX_TMP>; python3 - <<'E'
src=open('a.py').read()
src=src.replace("V=sum(F[k]*np.einsum('ac,db->abcd',C[k],C[k]) for k in (2,4)).astype(complex)",
"M=np.array([[[[1.0 if ms[a]+ms[b]==ms[c_]+ms[d] else 0 for d in range(5)] for c_ in range(5)] for b in range(5)] for a in range(5)])\n    V=(M*sum(F[k]*np.einsum('ac,db->abcd',C[k],C[k]) for k in (2,4))).astype(complex)")
open('a.py','w').write(src)
E
python3 -c "
from a import *
e=np.linalg.eigvalsh(H(0,900,3500,3));print(np.round(e-e.min()))
e=lev(900,900,3500,3);print(np.round(e-e.min()))
"