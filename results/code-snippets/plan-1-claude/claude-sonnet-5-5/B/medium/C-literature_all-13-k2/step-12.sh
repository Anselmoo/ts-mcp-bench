cd <SANDBOX_TMP>; cat > f.py <<'E'
from a import *
def quart(Dq,B):
    e=lev(Dq,B,4000,3); e=np.sort(e)
    g=[e[0],e[3],e[6],e[7]]  # T1,T2,A2,T1 (check via degeneracy)
    return e
def q3(x):
    e=np.sort(lev(x[0],x[1],4000,3)); u=[e[0],e[3],e[6],e[7]]
    # find levels by grouping
    return np.array([u[1]-u[0],u[2]-u[0],u[3]-u[0]])
tgt=np.array([7150,15200,19200])
r=least_squares(lambda x:q3(x)-tgt,[900,900],x_scale=[100,100])
print(r.x,q3(r.x))
Dq,B=r.x
for Cc in (3000,3500,4000,4500):
    e1=np.sort(lev(Dq,B,Cc,1));e3=np.sort(lev(Dq,B,Cc,3))
    e1=np.round(e1-e3[0],1)
    # remove quartet
    from collections import Counter
    cnt=Counter(e1); 
    q=Counter(np.round(e3-e3[0],1))
    d=[(k,v-q.get(k,0)) for k,v in sorted(cnt.items()) if v-q.get(k,0)>0]
    print(Cc,d[:12])
E
python3 f.py