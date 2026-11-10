from a import *
t=[19240,21890,23000]
def f(x):
    e=np.unique(np.round(lev(*x),2)); e=e[e>100]
    return e[:3]-t
for x0 in [(700,700,3000),(800,800,3500),(600,600,3400)]:
    r=least_squares(f,x0,x_scale=[100,100,100]);print(r.x,r.fun)
