cd /dev/shm/w && cat > fit.py <<'E'
from d7 import *
from scipy.optimize import least_squares
obs=np.array([8480,16305,20360,21001.])
def model(p):
    Dq,B,Cc=p
    e4,e2=levels(0,B,Cc,Dq)
    g=e4[0]
    q=sorted(set(np.round(e4-g,3)))
    # quartets: ground, 4T2, 4A2, 4T1(2)
    qs=[e4[3]-g,e4[6]-g,e4[7]-g]
    d=np.round(e2-g,2)
    # 2T1(2): triplet after the quartet-4T1(2)-ish: pick 2nd triplet above 2T2(1) -> index in e2 
    # e2 index: 15-17 (quartet 4T1(2)), 18-20 -> 21186 triplet
    return np.array(qs+[e2[18]-g])
for x0 in [(900,900,3900),(1000,800,3500),(800,950,4000)]:
    r=least_squares(lambda p:model(p)-obs,x0,x_scale=[100,100,300])
    print(r.x,r.fun,model(r.x))
E
python3 fit.py