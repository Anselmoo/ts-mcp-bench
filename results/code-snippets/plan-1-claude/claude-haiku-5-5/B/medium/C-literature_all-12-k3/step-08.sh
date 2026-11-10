cd <SANDBOX_TMP>/w && cat > fit2.py << 'EOF'
from ts import *
from scipy.optimize import least_squares
def quart_rel(Dq,B):
    q,_ = levels(Dq,B,4.0*B)
    g0=q[0]
    vals=[]
    for v in q:
        if not vals or abs(v-vals[-1][0])>1e-2: vals.append([v,1])
        else: vals[-1][1]+=1
    return [(v-g0,m) for v,m in vals]
def res(p):
    Dq,B = p
    qr = quart_rel(Dq,B)
    t2 = [v for v,m in qr if m==12][1]
    a2 = [v for v,m in qr if m==4][0]
    t1p = [v for v,m in qr if m==12][2]
    return np.array([t2-6150, a2-12400, t1p-16850])/100
sol = least_squares(res, [700,900], x_scale=[100,100])
print("Dq,B =", sol.x, "residuals(cm-1):", res(sol.x)*100)
print(quart_rel(*sol.x))
np.save('sol.npy', sol.x)
EOF
python3 fit2.py