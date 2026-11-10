cd /tmp/tsbench-run-tnbk5hz6; python3 - << 'EOF'
import sys; sys.path.insert(0,'.')
from ts import *
from scipy.optimize import least_squares
def model(p):
    Dq,B=p
    ev=singlets(Dq,B); g=groups(ev,1e-2); g0=g[0][0]
    t=[e-g0 for e,m in g if m==3 and e-g0>1]
    return t[:3]
def res2(p):
    t=model(p); return np.array([t[0]-16700,t[1]-26330])
s2_=least_squares(res2,[1850,810],x_scale=[1000,300],diff_step=1e-3)
print("fit nu1,nu2:",s2_.x, res2(s2_.x), "nu3 calc", model(s2_.x)[2])
# also ratio fit: nu2/nu1 with C=4B only ; Dq/B
for Dq,B in [(s2_.x[0],s2_.x[1])]:
    print("Dq/B",Dq/B)
EOF