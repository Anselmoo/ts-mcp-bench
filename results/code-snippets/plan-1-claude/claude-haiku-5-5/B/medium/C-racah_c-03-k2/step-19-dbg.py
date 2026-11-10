exec(open('fit2.py').read())
B,C,Dq=735.,3000.,1917.
F4=441*C/35; F2=(441*B+5*F4)/9
print("F2,F4",F2,F4)
g,gd=spectrum(F2,F4,Dq)
print("quartets",[(round(e,1),n) for e,n in g])
print("lowest doublets",[(round(e,1),n) for e,n in gd[:4]])
# analytic quartet T1 with 6Dq and 15B
import math
m=(6*Dq+15*B)/2; r=math.sqrt(((15*B-6*Dq)/2)**2+108*B*B)
print("analytic T1 pair (+12Dq shift):", m+12*Dq-r, m+12*Dq+r, " T2:",10*Dq)
