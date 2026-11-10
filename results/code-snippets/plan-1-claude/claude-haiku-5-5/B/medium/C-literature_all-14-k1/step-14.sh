
cd /tmp/tsbench-run-711ytt10/w && python3 -c "
from lab import labels
for B in [1e-3,100]:
    L=labels(1000.,B,4*B)
    print([ (round(x[1],1),x[2],x[3]) for x in L if x[0]==1.5])
" 2>&1 | grep -v "C4"