from b import *
from scipy.optimize import least_squares
def uniq(Dq,B):
    e=levels(Dq,B,4.6*B);e=e[e<1e5];e=e-e[0]
    u=[];
    for x in e:
        if not u or x-u[-1]>2: u.append(x)
    return np.array(u)
print(np.round(uniq(3000,600)[:8]))
obs=np.array([22640,22930,25080])
res=[]
for D0 in (2000,2500,3000,3500):
  for B0 in (400,600,800):
    r=least_squares(lambda p:uniq(*p)[1:4]-obs,[D0,B0],diff_step=1e-3)
    print(D0,B0,r.x,r.fun)
