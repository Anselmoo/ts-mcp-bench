import numpy as np
from scipy.optimize import brentq
from d3 import quartet, nus
v,m=quartet(0.0,1.0); print("Dq=0,B=1 levels:",np.round(v,5),m)
for x in [0.5,1.0,1.5,2.0,2.5]:
    v,m,n=nus(x); print("x=",x,"mult",m,"nu(4T2,4T1a,4T1b)=",np.round(n,4))
# Solve: nu1=10x*B (check), nu2/nu1=18500/12300, nu3/nu1=27900/12300 with B scaling
target2=18500/12300; target3=27900/12300
def f(x):
    v,m,n=nus(x); return n[1]/n[0]-target2
xs=brentq(f,0.5,3.0,xtol=1e-10)
v,m,n=nus(xs)
print("x=Dq/B =",xs," ratios:",n[1]/n[0],n[2]/n[0], "target3", target3)
print("nu(4T2) per B:",n[0])
B=12300/n[0]; Dq=xs*B
print("B =",B," Dq =",Dq, " C=",4.5*B)
print("predicted nu2,nu3 =", n[1]*B, n[2]*B)
