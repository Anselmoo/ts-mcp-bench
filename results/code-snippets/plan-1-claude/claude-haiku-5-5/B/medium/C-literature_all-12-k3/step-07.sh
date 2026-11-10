cd <SANDBOX_TMP>/w && cat > fit.py << 'EOF'
from ts import *
from scipy.optimize import least_squares
obs = dict(T2=6150., A2=12400., T1P=16850., D=19000.)
def pred(p):
    Dq,B,C = p
    q,d = levels(Dq,B,C)
    g0 = q[0]
    # quartet level groups: 12-fold groups & 4-fold
    qs = np.round(q,3)
    # unique levels with degeneracy
    vals=[]; 
    for v in q:
        if not vals or abs(v-vals[-1][0])>1e-2: vals.append([v,1])
        else: vals[-1][1]+=1
    return vals, d, g0
vals,d,g0 = pred((1000,1000,4000))
print("quartets:", [(round(v-g0,1),m) for v,m in vals])
dd=[]
for v in d:
    if not dd or abs(v-dd[-1][0])>1e-2: dd.append([v,1])
    else: dd[-1][1]+=1
print("doublets:", [(round(v-g0,1),m) for v,m in dd])
EOF
python3 fit.py