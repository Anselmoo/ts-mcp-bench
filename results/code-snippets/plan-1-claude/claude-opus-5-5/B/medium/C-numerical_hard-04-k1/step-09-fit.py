obs=np.array([29360,29620,31640.])
def res(x):
    s,u=dbl(*x); return u[1:4]-obs
best=None
for Dq0 in [2500,3000,3500,4000]:
  for B0 in [300,500,700,900]:
    r=least_squares(res,[Dq0,B0])
    if best is None or r.cost<best.cost: best=r
    print(Dq0,B0,r.x,r.fun, dbl(*r.x)[0])
print(best.x,best.fun,dbl(*best.x)[1][:8])
