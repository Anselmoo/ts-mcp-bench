from a import *
from scipy.optimize import least_squares
T=np.array([8480,16305,20360,21001.])
def groups(w):
    u=[]
    for x in w:
        if not u or abs(x-u[-1][0])>1: u.append([x,1])
        else: u[-1][1]+=1
    return u
def res(p):
    B,Cc,Dq=p
    u=groups(bands(B,Cc,Dq))
    e=[x for x,n in u if n in(12,)]  # quartet T
    a=[x for x,n in u if n==4]; d=[x for x,n in u if n==6]
    r=[]
    r.append(min(e,key=lambda x:abs(x-T[0]))-T[0])
    r.append(min(a,key=lambda x:abs(x-T[1]))-T[1])
    r.append(min(e[1:],key=lambda x:abs(x-T[2]))-T[2])
    r.append(min(d,key=lambda x:abs(x-T[3]))-T[3])
    return r
for g in [(900,3900,1000),(800,3500,1100),(950,4000,900)]:
    s=least_squares(res,g,diff_step=1e-3,x_scale=[100,400,100])
    print(s.x,s.fun)
