
cat > b.py <<'E'
from a import *
def f(x):
    Dq,B=x; L=levels(Dq,B,4.5*B)
    e=[l[0]-L[0][0] for l in L if l[1]==3]
    return [e[0]-16611,e[1]-23529]
for g in [(2000,500),(2500,400),(1800,600)]:
    r=least_squares(f,g,x_scale=[1000,100]); print(r.x,r.fun)
E
python3 b.py