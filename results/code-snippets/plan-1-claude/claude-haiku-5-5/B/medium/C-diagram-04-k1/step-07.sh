cd ~ 2>/dev/null; cd /tmp/tsbench-run-r46p2nmr && python3 -c "
import ts, numpy as np
from ts import *
Dq=2.0
h = -4*Dq*np.eye(5) + 10*Dq*Peg
H1 = restrict(one_body_op(h))
Htot = H1 + H2_6 + LAM*S2_6
w, Vv = np.linalg.eigh((Htot+Htot.conj().T)/2)
Svals = np.real(np.einsum('ij,ik,kj->j', Vv.conj(), S2_6, Vv))
import collections
print(collections.Counter(np.round(Svals,3)))
print(np.round(w[:12],4))
print(np.round(w[-5:],4))
print('hermitian err', np.abs(H1-H1.conj().T).max(), np.abs(H2_6-H2_6.T).max())
" 2>&1 | tail -20