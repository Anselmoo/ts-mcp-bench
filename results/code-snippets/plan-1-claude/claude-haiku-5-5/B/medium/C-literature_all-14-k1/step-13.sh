
cd /tmp/tsbench-run-711ytt10/w && python3 -c "
from lab import labels
for B in [0,1e-3,300,1000]:
    L=labels(1000.,B,4*B)
    g=[x for x in L if x[0]==1.5 and x[2]==12 and x[3]==4][0][1]
    t2=[x for x in L if x[0]==1.5 and x[2]==12 and x[3]==-4][0][1]
    print(B, round(t2-g,2))
" 2>&1 | grep -v "C4"