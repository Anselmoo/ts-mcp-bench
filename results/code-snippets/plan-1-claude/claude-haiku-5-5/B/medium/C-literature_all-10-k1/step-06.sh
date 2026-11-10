cd /tmp/tsbench-run-gtq3enrs; python3 - << 'EOF'
import itertools
dets = [tuple(sorted(c)) for c in itertools.combinations(range(10),6)]
didx={d:i for i,d in enumerate(dets)}
def create(i, st):
    if i in st: return None
    p = sum(1 for m in st if m<i); return ((-1)**p, tuple(sorted(st+(i,))))
perm = {0:(0,-1),1:(2,1),2:(1,-1),3:(3,-1),4:(4,1)}
st=(0,1,2,3,4,5)
sign=1;cur=()
for m in st:
    o,s=divmod(m,2); no,sg=perm[o]; sign*=sg
    r=create(2*no+s,cur); ss,cur=r; sign*=ss
print(sign,cur)
EOF