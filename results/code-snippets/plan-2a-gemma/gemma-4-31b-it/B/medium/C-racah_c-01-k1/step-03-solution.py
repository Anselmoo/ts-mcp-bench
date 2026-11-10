import numpy as np
from scipy.optimize import minimize

def objective(vars):
    B, Dq = vars
    nu1_calc = 10 * Dq
    # T1g roots:
    # E^2 - (15B + 10Dq)E + (100Dq^2 + 15B*10Dq) = 0 (This was my guess)
    # Let's try the most general T1g roots:
    # The matrix for T1g is:
    # [[15B, sqrt(120B*10Dq)], [sqrt(120B*10Dq), 15B + 10Dq]] - No.
    # Let's use the one from a known source:
    # E(T1g) = 0.5 * (15B + 10Dq +/- sqrt((15B - 10Dq)^2 + 120B*10Dq))
    # Wait, I already tried that.
    
    # Let's try:
    # nu1 = 10Dq
    # nu2 = 0.5 * (15B + 10Dq - sqrt((15B-10Dq)^2 + 120B*10Dq))
    # nu3 = 0.5 * (15B + 10Dq + sqrt((15B-10Dq)^2 + 120B*10Dq))
    # Wait, I already tried that too.
    
    # What if the formulas are:
    # nu1 = 10Dq
    # nu2 = 0.5 * (15B + 10Dq - sqrt(225B^2 + 120B*10Dq + 100Dq^2)) - No.
    
    # Let's try the most standard d3 formulas:
    # E(4A2g) = 0
    # E(4T2g) = 10Dq
    # E(4T1g(F)) = 0.5 * (15B + sqrt(225B^2 + 120B*10Dq + 100Dq^2)) - 10Dq - No.
    
    # Let's use the ones from a source that I trust:
    # E(4A2g) = 0
    # E(4T2g) = 10Dq
    # E(4T1g(F)) = 15B + 10Dq - E(4T1g(P))
    # E(4T1g(P)) = 0.5 * (15B + 10Dq + sqrt((15B-10Dq)^2 + 120B*10Dq))
    # This is exactly what I had before.
    
    # Let's try to fit B and Dq to nu1, nu2, nu3 using these:
    nu1_obs, nu2_obs, nu3_obs = 14170, 21710, 33970
    
    # Try to find B and Dq such that they match nu1, nu2, nu3.
    # But we have 3 equations and 2 unknowns.
    
    # Maybe nu1 is NOT 10Dq? No, for d3 it must be.
    # Let's use the ratios nu2/nu1 and nu3/nu1.
    # nu2/nu1 = 21710 / 14170 = 1.532
    # nu3/nu1 = 33970 / 14170 = 2.397
    
    # In a Tanabe-Sugano diagram for d3:
    # If nu2/nu1 = 1.532, then B/Dq is approximately...
    # Let's check a TS diagram. For d3, nu2/nu1 = 1.532 occurs at B/Dq ~ 0.8.
    # Let's check nu3/nu1 for B/Dq = 0.8.
    # 10Dq = 14170 => Dq = 1417
    # B = 0.8 * 1417 = 1133.6
    # 15B = 16999.7, 10Dq = 14170
    # nu2 = 0.5 * (16999.7 + 14170 - sqrt((16999.7-14170)**2 + 120*1133.6*14170))
    # nu2 = 0.5 * (31169.7 - sqrt(2829.7^2 + 1928000000)) = 0.5 * (31169.7 - 43915) = -6372.
    # Still negative! My T1g formula is definitely wrong.
    
    return 0

print("Still searching for the right formula...")
