python3 - << 'EOF'
import numpy as np, itertools
from scipy.optimize import least_squares
d=np.load('<SANDBOX_TMP>/lv.npz')
Mcf,M2,M4=d['Mcf'],d['M2'],d['M4']
import itertools
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
dets=list(itertools.combinations(range(10),7))
Sz=np.array([sum(0.5*orbs[i][1] for i in dd) for dd in dets])
i3=np.where(np.isclose(Sz,1.5))[0]; i1=np.where(np.isclose(Sz,0.5))[0]
def H(p):
    Dq,B,C=p; F4=12.6*C; F2=49*B+5*F4/9
    return Dq*Mcf+F2*M2+F4*M4
def levels(p):
    Hm=H(p)
    q=np.linalg.eigvalsh(Hm[np.ix_(i3,i3)])
    dl=list(np.linalg.eigvalsh(Hm[np.ix_(i1,i1)]))
    for x in q:
        j=int(np.argmin([abs(y-x) for y in dl])); dl.pop(j)
    return np.sort(q), np.sort(np.array(dl))
# quartet levels distinct
def quart(p):
    q,_=levels(p)
    # distinct groups of 3/1
    vals=[q[0]]
    out=[]
    for x in q:
        if not out or abs(x-out[-1])>1e-3: out.append(x)
    return np.array(out)  # T1F, T2F, A2F, T1P
# doublet T-type levels: identify by 3-fold degeneracy
def dT(p):
    _,dd=levels(p)
    out=[];k=0
    while k<len(dd):
        grp=[dd[k]]
        j=k+1
        while j<len(dd) and abs(dd[j]-dd[k])<1e-3: grp.append(dd[j]); j+=1
        out.append((dd[k],len(grp))); k=j
    return out
p0=(850,900,3500)
qq=quart(p0)
print("quartets rel:",np.round(qq-qq[0],1))
print("doublet levels:",[(round(e-qq[0],1),n) for e,n in dT(p0)])
def res(x, which):
    Dq,B,C=x
    qq=quart(x)
    dts=dT(x)
    E=[qq[1]-qq[0], qq[2]-qq[0], qq[3]-qq[0]]
    # which doublet T index
    dlev=[e-qq[0] for e,n in dts if n==3]
    return np.array([E[0]-8480,E[1]-16305,E[2]-20360, dlev[which]-21001])
# try each candidate doublet T index
for which in range(0,8):
    try:
        r=least_squares(lambda x:res(x,which),[850,900,3500],bounds=([0,200,0],[3000,2000,9000]))
        print(which, np.round(r.x,1), np.round(r.fun,2))
    except Exception as e: print(which,e)
EOF