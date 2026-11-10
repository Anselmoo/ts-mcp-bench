
cd $(ls -td <SANDBOX_TMP>/tmp.* | head -1) && python3 - << 'EOF'
src=open('d3.py').read().split("from scipy.optimize import brentq")[0].replace("for l in levels(1917,824,3300)[:8]: print(l)","")
exec(src)
from scipy.optimize import brentq
up=[idx[d] for d in dets if all(orbs[o][1]==1 for o in d)]
def q(Dq,B,C):
    M=H(Dq,B,C);e=np.linalg.eigvalsh(M);g=e[0]
    qe=np.linalg.eigvalsh(M[np.ix_(up,up)])-g
    u=[];[u.append(x) for x in qe if not u or abs(x-u[-1])>1e-3]
    E2=[x for x,gg in levels(Dq,B,C) if gg==4][1]
    return u,E2
print(q(1917,824,3300))
def res(p):
    B,C=p;qe,E2=q(1917,B,C);return [qe[2]-27260,qe[3]-42610,E2-17050]
s=least_squares(res,[824,3300]);print(s.x,res(s.x))
def res2(p):
    Dq,B,C=p;qe,E2=q(Dq,B,C);return [qe[1]-19170,qe[2]-27260,qe[3]-42610,E2-17050]
s=least_squares(res2,[1917,824,3300]);print(s.x,res2(s.x))
EOF
