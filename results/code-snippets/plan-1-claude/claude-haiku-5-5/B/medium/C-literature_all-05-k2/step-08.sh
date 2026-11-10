cd /tmp/tsbench-run-7__jfl5e; cat > fit2.py << 'EOF'
from an import *
from scipy.optimize import least_squares
def clusters(vals,tol=2.0):
    vals=np.sort(vals); out=[]; cur=[vals[0]]
    for x in vals[1:]:
        if x-cur[-1]<tol: cur.append(x)
        else: out.append((np.mean(cur),len(cur))); cur=[x]
    out.append((np.mean(cur),len(cur))); return out
def spectrum(p):
    Dq,B,C=p
    eq,ed=levels(Dq,B,C)
    return clusters(eq), clusters(ed)
def resid(p):
    q,dd=spectrum(p)
    E0=q[0][0]
    t2=[e-E0 for e,m in q if m==12 and e-E0>1]
    t1=[e-E0 for e,m in q if m==12 and e-E0>1]
    e2=[e-E0 for e,m in dd if m==2]
    return t2,t1,e2
p=[2155,600,3000]
q,dd=spectrum(p)
print("quartets",[(round(e-q[0][0]),m) for e,m in q])
print("doublets",[(round(e-q[0][0]),m) for e,m in dd])
EOF
python3 fit2.py 2>&1 | tail -4