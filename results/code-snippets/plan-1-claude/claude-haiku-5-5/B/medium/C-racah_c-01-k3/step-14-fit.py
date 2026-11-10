from ts import *
from scipy.optimize import least_squares
def Fk(B,C):
    F4=35*0+ 441*C/35; F2=(441*B+5*F4)/9
    return {0:0.0,2:F2,4:F4}
def spectrum(B,C,Dq):
    F=Fk(B,C)
    q,_=Hmat(F,Dq,Sz2=3); H1,_=Hmat(F,Dq,Sz2=1)
    eq=np.sort(np.linalg.eigvalsh(q)); e1=np.sort(np.linalg.eigvalsh(H1))
    rem=list(e1)
    for x in eq:
        j=min(range(len(rem)),key=lambda i:abs(rem[i]-x)); rem.pop(j)
    return eq, np.sort(np.array(rem))
def levels(B,C,Dq):
    eq,ed=spectrum(B,C,Dq)
    g=eq[0]  # ground 4A2g
    return eq-g, ed-g
if __name__=="__main__":
    import sys
    eq,ed=levels(900.,4000.,1000.)
    print("quartets",np.round(np.unique(np.round(eq,2)),1))
    print("doublets",np.round(np.unique(np.round(ed,2)),1))
