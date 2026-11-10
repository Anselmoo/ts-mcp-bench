from scipy.optimize import brentq
def q(Dq,B,C):
    M=H(Dq,B,C);e,v=np.linalg.eigh(M);e=e-e[0]
    up=[idx[d] for d in dets if all(orbs[o][1]==1 for o in d)]
    qe=sorted(set(np.round([e[i] for i in range(len(e)) if np.sum(v[up,i]**2)>0.5],3)))
    lv=levels(Dq,B,C); E2=[x for x,g in lv if g==4][1]
    return qe,E2
def res(p):
    B,C=p;qe,E2=q(1917,B,C)
    return [qe[2]-27260,qe[3]-42610,E2-17050]
s=least_squares(res,[824,3300]);print(s.x,res(s.x),q(1917,*s.x)[0])
print(brentq(lambda C:q(1917,824,C)[1]-17050,2000,5000))
