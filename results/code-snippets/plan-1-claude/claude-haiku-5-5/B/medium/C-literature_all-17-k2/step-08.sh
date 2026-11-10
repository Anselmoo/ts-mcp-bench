cat > fit.py << 'EOF'
from d8 import *
from scipy.optimize import least_squares
def model(p):
    Dq,B,C=p
    r=levels(Dq,B,C)
    t=r[2]; g=t[0]
    T2=t[1]-g; T1F=t[4]-g; T1P=t[7]-g
    s=r[0]
    # remove triplet eigenvalues from Sz=0 list
    rem=list(s)
    for v in t:
        i=int(np.argmin([abs(x-v) for x in rem])); rem.pop(i)
    rem=np.array(rem)
    E1=rem[0]-g  # lowest singlet (should be 1E)
    return np.array([T2,T1F,T1P,E1]), rem
# identify ladder: triplet sorted: [A2(1), T2(3), T1F(3), T1P(3)]
t_idx_check=True
obs=np.array([9770,16050,26740,12987.])
def res(p):
    m,_=model(p)
    return (m-obs)/1000.
sol=least_squares(res,[970,800,3500],x_scale=[100,100,500])
print("Dq,B,C =",sol.x, "resid",res(sol.x)*1000)
m,rem=model(sol.x); print("model",m)
print("singlets rel", np.round(rem-model.__defaults__ if False else rem[:6],1))
EOF
python3 fit.py