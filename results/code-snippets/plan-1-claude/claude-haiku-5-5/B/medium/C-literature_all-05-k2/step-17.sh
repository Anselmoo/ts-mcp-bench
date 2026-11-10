cd /tmp/tsbench-run-7__jfl5e; cat > solve.py << 'EOF'
from fit4 import *
def res(x):
    B,C=x; Dq=2155.0
    g,dd=spec((Dq,B,C)); E0=g[0]
    cq=clus(g); t1f=[e-E0 for e,m in cq if m==12][0]  # lower 12-fold after 4T2? use index
    t2=[e-E0 for e,m in cq if m==12]
    e2=[e-E0 for e,m in clus(dd) if m==4][0]
    return [t2[0]-21550, t2[1]-28500, e2-15200]
sol=least_squares(lambda x: res(x)[:2]+[0], [600,3000], bounds=([100,500],[1500,6000]))
for x0 in [(600,3000),(700,3500),(500,2500)]:
    s=least_squares(lambda x: res(x)[1:3], x0)
    print("fit",np.round(s.x,1), np.round(res(s.x),1))
EOF
python3 solve.py 2>&1 | grep fit