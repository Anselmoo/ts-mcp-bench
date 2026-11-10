import numpy as np, d3
from scipy.optimize import brentq
def f(B,C):
    s=d3.spectrum(B,C); g=s['Q'][0][0]
    T1=[x-g for x,m in s['Q'] if m==12][1]
    E2=[x-g for x,m in s['D'] if m==4][0]
    return T1,E2
# for C: find B so T1F=32500 then see E2
for C in [2800,3200,3600,4000,4400]:
    try:
        B=brentq(lambda b: f(b,C)[0]-32500, 400,1200, xtol=0.5)
        print(C, round(B,1), [round(v,1) for v in f(B,C)])
    except Exception as e: print(C,'err',e)
