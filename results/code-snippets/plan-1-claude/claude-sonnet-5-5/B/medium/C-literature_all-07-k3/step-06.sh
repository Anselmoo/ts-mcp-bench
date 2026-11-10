cd /dev/shm/w && cat > f.py <<'E'
from a import *
from scipy.optimize import least_squares
def res(x):
    Dq,B=x;C=(23000-10*B)/5
    w=levels(energies(Dq,B,C))
    return [w[1][0]-19240,w[2][0]-21890]
for g in [(700,700),(800,600),(600,800)]:
    r=least_squares(res,g);print(r.x,r.fun,(23000-10*r.x[1])/5)
E
python3 f.py