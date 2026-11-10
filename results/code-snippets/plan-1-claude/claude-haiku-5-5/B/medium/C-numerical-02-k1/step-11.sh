sed -i 's/s+=A\[(k,m1,m3,q)\]\*np.conj(A\[(k,m2,m4,q)\])/s+=np.conj(A[(k,m3,m1,q)])*A[(k,m2,m4,q)]/' d7.py && grep -n "s+=" d7.py && cd .. && python3 -c "
import sys; sys.path.insert(0,'d7')
" ; cd /tmp/tsbench-run-aa74wow9/d7 && python3 -c "
from run import *
import collections
for F in [(1,0),(0,1)]:
    w,S=levels(0,0,*F)
    q=collections.Counter(sorted([round(e,5) for e,s in zip(w,S) if abs(s-3.75)<1e-3]))
    print(F,q)
"