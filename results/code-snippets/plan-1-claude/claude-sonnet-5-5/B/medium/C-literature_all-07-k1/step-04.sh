
cd <SANDBOX_TMP>; cat > b.py <<'E'
from a import *
t=np.array([19240,21890,23000])
def f(x):
    e=lev(*x); e=e[e>100]
    g=[e[0]]
    for v in e[1:]:
        if v-g[-1]>1: g.append(v)
        if len(g)==3:break
    return np.array(g)-t
for x0 in [(700,700,3000),(800,800,3500),(600,600,3400),(900,600,3000)]:
    r=least_squares(f,x0,diff_step=1e-3);print(r.x,r.fun)
E
python3 b.py