cd <SANDBOX_TMP>/w && python3 -c "
from fit import *
obs=np.array([18850,19750,20560])
def res(p):
    g,t=trip(*p); return np.array([x[0] for x in t[1:4]])-obs
for x0 in [(2000,400),(2500,700),(3000,300),(2200,900)]:
    r=least_squares(res,x0); print(r.x,r.fun, trip(*r.x)[0], trip(*r.x)[1][:5])
"