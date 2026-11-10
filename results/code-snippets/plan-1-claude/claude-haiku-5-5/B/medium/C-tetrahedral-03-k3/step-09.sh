cd <SANDBOX_TMP>/w && cat > fit2.py << 'EOF'
from fit import levels
from scipy.optimize import least_squares
obs=np.array([3600,7870,16410.])
def bands(p):
    Dq,B,C=p
    lv=levels(Dq,B,C)
    g=lv[0][0]
    return np.array([lv[1][0]-g, lv[2][0]-g, lv[3][0]-g])
def res(p): return (bands(p)-obs)/obs
for C0 in [3000,4000,5000]:
    s=least_squares(res,[400,800,C0],x_scale=[100,100,500])
    print(np.round(s.x,2), np.round(bands(s.x),2), np.max(np.abs(s.fun)))
EOF
python3 fit2.py 2>&1 | grep -v Shell | tail -5