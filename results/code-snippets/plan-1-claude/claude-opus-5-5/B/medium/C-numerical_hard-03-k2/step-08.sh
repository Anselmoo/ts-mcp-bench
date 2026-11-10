
cd $TMPDIR && cat << 'EOF' > fit2.py
exec(open('grid.py').read().split('obs=')[0])
from scipy.optimize import least_squares
obs=np.array([22640,22930,25080])
def f(p):
    w,s=lev(*p); D=np.unique(np.round(w[s<1],4)); return D[1:4]-D[0]-obs
for x0 in [[2700,825],[2750,950],[2650,700]]:
    r=least_squares(f,x0,diff_step=1e-5)
    w,s=lev(*r.x)
    ww=np.unique(np.round(w,3));
    print(r.x,f(r.x),'ground S2',round(s[0],2), 'lowest levels',[(round(a-w[0]),round(s[np.argmin(abs(w-a))],2)) for a in ww[:8]])
EOF
timeout 110 python3 fit2.py
