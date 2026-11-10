
cd /tmp/tsbench-run-la9r0a6w && sed -i "s/r=cre_ann(\[('c',p),('a',q)\], s)/r=cre_ann([('a',q),('c',p)], s)/; s/r=cre_ann(\[('c',p),('c',q),('a',s_),('a',r_)\], s)/r=cre_ann([('a',r_),('a',s_),('c',q),('c',p)], s)/" d3.py && grep -n cre_ann d3.py && python3 fit.py && python3 -c "
from d3 import *
for F2,F4 in [(1,0),(0,1)]:
    print(np.round(np.linalg.eigvalsh(build(F2,F4,0.0)),4))"