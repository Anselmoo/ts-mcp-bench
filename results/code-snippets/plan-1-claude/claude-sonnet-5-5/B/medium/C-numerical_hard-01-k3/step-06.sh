
cd /dev/shm
cat > b.py <<'E'
exec(open('a.py').read().split("M=H(900")[0])
def lev(B,C,Dq):
    t=trip(B,C,Dq);u=[t[0]]
    for x in t[1:]:
        if x-u[-1]>1: u.append(x)
    return np.array(u)-u[0]
print(lev(900,4230,2000)[:8])
obs=np.array([18850,19750,20560])
def res(p): return lev(p[1],4.7*p[1],p[0])[1:4]-obs
for g in [(2000,600),(2400,700),(1800,900),(2800,500),(2200,800)]:
    r=least_squares(res,g,x_scale=[100,50]);print(g,r.x,r.fun)
E
python3 b.py