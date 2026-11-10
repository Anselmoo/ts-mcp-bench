cd <SANDBOX_TMP>; sed "s/(-1)\*\*q\*C3\[(k,a\[0\],cc\[0\])\]\*C3\[(k,d\[0\],b\[0\])\]/C3[(k,a[0],cc[0])]*C3[(k,d[0],b[0])]/" a.py > g.py
cat > f.py <<'E'
from g import *
def three(p):
    e=lev(*p); u=[]
    for x in e[1:]:
        if not u or abs(x-u[-1])>1: u.append(x)
    return u[:3]
t=np.array([19720,23260,24980])
r=least_squares(lambda p:np.array(three(p))-t,[800,800,3000],x_scale=[100,100,300],diff_step=1e-4)
print(r.x,three(r.x))
E
python3 f.py