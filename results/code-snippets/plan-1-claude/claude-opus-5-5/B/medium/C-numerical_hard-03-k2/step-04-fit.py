exec(open('d5.py').read())
from scipy.optimize import least_squares
obs=np.array([22640,22930,25080])
def ex(p):
    L=levels(p[0],p[1],4.6*p[1])
    g=L[0][0]; assert L[0][2]<1
    d=[x[0]-g for x in L[1:] if x[2]<1]
    return np.array(d[:3]),L
best=None
for Dq0 in [2000,2500,3000,3500]:
  for B0 in [300,500,700]:
    r=least_squares(lambda p:ex(p)[0]-obs,[Dq0,B0],diff_step=1e-4)
    if best is None or r.cost<best.cost: best=r
print(best.x,best.cost,ex(best.x)[0])
L=ex(best.x)[1];g=L[0][0]
for x in L[:12]: print(round(x[0]-g),x[1],x[2])
