cd <SANDBOX_TMP>; cat > h.py <<'E'
from g import *
def model(x):
    Dq,B,Cc=x
    e=np.sort(lev(Dq,B,Cc,3)); q=[e[3]-e[0],e[6]-e[0],e[7]-e[0]]
    l=ident(Dq,B,Cc)
    qe=np.round(e-e[0],1)
    t=[E for (E,n,ch) in l if n==3 and ch>0.5 and not np.any(abs(qe-E)<1.0)]
    return np.array(q+[t[1]])
tgt=np.array([7150,15200,19200,21130])
r=least_squares(lambda x:model(x)-tgt,[815,878,3900],x_scale=[50,50,200],diff_step=1e-3)
print(r.x,model(r.x))
E
python3 h.py