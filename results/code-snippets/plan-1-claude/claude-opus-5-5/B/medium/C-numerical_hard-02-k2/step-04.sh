
cd $TMPDIR && cat > fit.py << 'EOF'
import sys; sys.path.insert(0,'.')
from d4 import *
from scipy.optimize import least_squares
obs=np.array([22900,23730,24580])
def res(p):
    Dq,B=p; g=levels(Dq,B,4.3*B); E0=g[0][0]
    assert g[0][1]==3
    return np.array([g[i][0]-E0 for i in (1,2,3)])-obs
r=least_squares(res,[2500,700])
print(r.x,res(r.x))
Dq,B=r.x; g=levels(Dq,B,4.3*B)
print([(round(x-g[0][0]),n) for x,n in g[:6]])
EOF
python3 fit.py
