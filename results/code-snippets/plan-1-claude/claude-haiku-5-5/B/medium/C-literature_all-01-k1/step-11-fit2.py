print("Dq=500,B=1000:", [(round(float(e),1),n) for e,n in levels(1000,500)])
from scipy.optimize import fsolve
def model(p):
    Dq,B=p
    L=levels(B,Dq)
    E=[float(e) for e,n in L]; N=[n for e,n in L]
    return E,N
for Dq in [300,400,500]:
    E,N=model_out=None,None
