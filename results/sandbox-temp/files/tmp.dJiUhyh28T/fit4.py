exec(open('pre.py').read())
from scipy.optimize import least_squares
obs=np.array([7150,15200,19200,21130.])
def pred(p):
    r=levels_fast(*p)
    q=r[1.5]; d=r[0.5]
    g=q[0][0]
    t2=[x for x in q if x[2]==-4 and x[1]==12][0][0]
    a2=[x for x in q if x[1]==4][0][0]
    t1p=q[3][0]
    dt1=[x[0] for x in d if x[2]==2 and x[1]==6]
    return np.array([t2-g,a2-g,t1p-g,dt1[1]-g])
def res(p): return pred(p)-obs
print(pred([715,900,3500]))
s=least_squares(res,[800,900,3000],bounds=([300,300,500],[1500,1500,7000]),x_scale=[50,50,300])
print("fit",s.x.round(1),"pred",pred(s.x).round(1),"res",s.fun.round(1))
