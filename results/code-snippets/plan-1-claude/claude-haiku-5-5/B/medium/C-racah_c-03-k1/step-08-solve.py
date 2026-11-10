from fit import *
obs = np.array([19170.,27260.,42610.,17050.])
def model(p):
    Dq,B,C = p
    q,d = levels(Dq,B,C)
    return np.array([q[1]-q[0], q[4]-q[0], q[7]-q[0], d[0]-q[0]])
def res(p): return (model(p)-obs)
best=None
for B0 in [600,800,1000]:
    for C0 in [3000,4000,4500]:
        r = least_squares(res,[1917,B0,C0],x_scale=[1000,500,1000])
        if best is None or r.cost<best.cost: best=r
print("params Dq,B,C:", best.x)
print("model:", model(best.x)); print("resid:", best.fun)
print("C/B", best.x[2]/best.x[1])
