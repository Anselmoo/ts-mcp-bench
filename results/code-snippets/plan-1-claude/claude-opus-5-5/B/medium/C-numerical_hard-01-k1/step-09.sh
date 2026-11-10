cat > fit.py <<'EOF'
from d4 import *
def lev(Dq,B):
    t=triplets(Dq,B,4.7*B); 
    u=[]
    for x in t:
        if not u or abs(x-u[-1])>1e-3: u.append(x)
    return [x-u[0] for x in u]
obs=[18850,19750,20560]
def res(p):
    l=lev(*p)[1:4]; return [a-b for a,b in zip(l,obs)]
p=[2200.,600.]
for it in range(15):
    r=res(p);J=[]
    for i,h in enumerate([1.,1.]):
        q=p[:];q[i]+=h;rq=res(q);J.append([(a-b)/h for a,b in zip(rq,r)])
    # normal eq
    a11=sum(x*x for x in J[0]);a12=sum(x*y for x,y in zip(J[0],J[1]));a22=sum(y*y for y in J[1])
    b1=-sum(x*y for x,y in zip(J[0],r));b2=-sum(x*y for x,y in zip(J[1],r))
    det=a11*a22-a12*a12
    d1=(b1*a22-b2*a12)/det;d2=(a11*b2-a12*b1)/det
    p=[p[0]+d1,p[1]+d2]
print(p,res(p))
print(lev(*p)[:8])
t=triplets(p[0],p[1],4.7*p[1]);q=jacobi(H(4,p[0],p[1],4.7*p[1]))
print("quintet low - triplet ground", q[0]-t[0])
EOF
python3 fit.py