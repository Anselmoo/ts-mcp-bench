cd <SANDBOX_TMP> && cat > f.py <<'E'
from a import *
obs=np.array([13960,22740,29700])
f=lambda p:np.array([l[0] for l in levels(singlets(p[0],p[1],4.5*p[1]),3)])-obs
r=least_squares(f,[1600,500],diff_step=1e-3,x_scale=[1000,300]); print(r.x,r.fun,levels(singlets(r.x[0],r.x[1],4.5*r.x[1]),4))
E
timeout 550 python3 f.py