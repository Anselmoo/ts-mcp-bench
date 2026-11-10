cd /dev/shm && cat > b.py <<'E'
exec(open('a.py').read().split("D={ms")[0])
D={ms:build(ms) for ms in (1,3)}
import numpy as np
st1=[s for s in itertools.combinations(range(10),7) if sum(1 if o%2==0 else -1 for o in s)==1]
M1=np.array([sum(orbs[o][0] for o in s) for s in st1])
ph=np.exp(-1j*np.pi/2*M1)
def lev(Dq,B,C):
    hd,T2,T4=D[3]; e3=np.linalg.eigvalsh(Dq*hd+(49*B+7*C)*T2+(63*C/5)*T4)
    hd,T2,T4=D[1]; e,v=np.linalg.eigh(Dq*hd+(49*B+7*C)*T2+(63*C/5)*T4)
    e0=e.min()
    q=groups(e3-e0 if False else e3-e3.min())
    qs=[g[0] for g in q]
    e=e-e0
    out=[]
    for g,(x,dg) in zip(range(0),[]): pass
    gs=groups(e)
    i=0;res=[]
    for x,dg in gs:
        V=v[:,i:i+dg]; chi=sum((abs(V[:,k])**2*ph).sum() for k in range(dg)).real; i+=dg
        isq=any(abs(x-y)<1e-3 for y in qs)
        res.append((x,dg,round(chi,2),isq))
    return qs,res
qs,res=lev(900,900,3900)
print(qs)
for r in res[:10]: print(r)
def f(p):
    qs,res=lev(*p)
    d=[r[0] for r in res if not r[3] and r[1]==3 and abs(r[2]-1)<.1]
    return [qs[1]-8100,qs[3]-19400,d[1]-21600]
for x0 in [(900,900,3900),(1000,800,3500),(850,950,4000)]:
    s=least_squares(f,x0,x_scale=[100,100,300]);print(s.x,s.fun)
    qs,res=lev(*s.x);print(qs);print([r for r in res[:12]])
E
python3 b.py