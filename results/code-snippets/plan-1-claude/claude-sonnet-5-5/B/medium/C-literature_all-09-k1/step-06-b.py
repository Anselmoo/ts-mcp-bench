import sys; sys.path.insert(0,'/dev/shm')
from a import *
T=[19720,23260,24980]
def err(p):
    L=levels(*p)[1:4]
    return sum((x-t)**2 for x,t in zip(L,T))
# 3 params B,C,D ; Nelder-Mead from several starts
def nm(x0,step):
    pts=[x0]+[[x0[i]+(step[i] if i==j else 0) for i in range(3)] for j in range(3)]
    fs=[err(p) for p in pts]
    for it in range(400):
        o=sorted(range(4),key=lambda i:fs[i]);pts=[pts[i] for i in o];fs=[fs[i] for i in o]
        c=[sum(p[i] for p in pts[:3])/3 for i in range(3)]
        r=[c[i]+(c[i]-pts[3][i]) for i in range(3)];fr=err(r)
        if fr<fs[0]:
            e=[c[i]+2*(c[i]-pts[3][i]) for i in range(3)];fe=err(e)
            pts[3],fs[3]=(e,fe) if fe<fr else (r,fr)
        elif fr<fs[2]: pts[3],fs[3]=r,fr
        else:
            k=[c[i]+0.5*(pts[3][i]-c[i]) for i in range(3)];fk=err(k)
            if fk<fs[3]: pts[3],fs[3]=k,fk
            else:
                for j in range(1,4):
                    pts[j]=[pts[0][i]+0.5*(pts[j][i]-pts[0][i]) for i in range(3)];fs[j]=err(pts[j])
        if fs[0]<1e-6: break
    return pts[0],fs[0]
for x0 in ([700,3000,700],[900,3500,900],[600,3200,1000],[800,3000,500]):
    p,e=nm(x0,[50,100,50]);print(p,e,levels(*p)[1:5])
