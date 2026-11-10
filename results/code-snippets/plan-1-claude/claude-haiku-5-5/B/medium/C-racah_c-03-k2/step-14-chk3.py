import numpy as np
exec(open('run_d3.py').read().split('H2=two_body')[0])
# orthonormality of Y2m
G=np.array([[np.sum(W*np.conj(Y(2,a,TH,PH))*Y(2,c,TH,PH)) for c in ms] for a in ms])
print(np.round(G,6).real.diagonal())
# Gaunt <2 0|C2_0|2 0> check: int Y20* Y20 Y20 = sqrt(5/(4pi))*(2 2 2;0 0 0)^2 * sqrt(5*5*5/(4pi))?? just print
print("int Y20^3 =", np.sum(W*Y(2,0,TH,PH)**3).real, " sqrt(5/4pi)*2/7*...")
print("A2[2,2,q=0] =", A[2][2,2,2], " B2 =",B[2][2,2,2])
print("int Y20 Y20* Y20 =", np.sum(W*np.conj(Y(2,0,TH,PH))*np.conj(Y(2,0,TH,PH))*Y(2,0,TH,PH)))
