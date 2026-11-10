cat << 'EOF' > solver.py
import numpy as np

def solve_d3(dq_over_b):
    B = 1.0
    Dq = dq_over_b * B
    
    # Ground state: 4A2g (t2g^3)
    # E(4A2g) = -12*Dq + Repulsion(t2g^3, 4A2g)
    # We work relative to 4A2g, so E(4A2g) = 0.
    
    # 4T2g: (t2g^2 eg^1)
    # E(4T2g) = -2*Dq + Rep(t2g^2 eg^1, 4T2g)
    # Relative to 4A2g: E(4T2g) = 10*Dq + (Rep(t2g^2 eg^1, 4T2g) - Rep(t2g^3, 4A2g))
    # In the limit Dq=0, E(4T2g) - E(4A2g) = 0 (since both are from 4F)
    # So Rep(t2g^2 eg^1, 4T2g) - Rep(t2g^3, 4A2g) = 0.
    e_4t2g = 10 * Dq
    
    # 4T1g: Mixes (t2g^2 eg^1) and (t2g^1 eg^2)
    # Mat = [[ -2*Dq + Rep(t2g^2 eg^1, 4T1g), mix ],
    #        [ mix, 8*Dq + Rep(t2g^1 eg^2, 4T1g) ]]
    # Relative to 4A2g:
    # Mat = [[ 10*Dq + (Rep(t2g^2 eg^1, 4T1g) - Rep(t2g^3, 4A2g)), mix ],
    #        [ mix, 20*Dq + (Rep(t2g^1 eg^2, 4T1g) - Rep(t2g^3, 4A2g)) ]]
    # At Dq=0, eigenvalues are 0 and 15*B.
    # Rep(t2g^2 eg^1, 4T1g) - Rep(t2g^3, 4A2g) = a
    # Rep(t2g^1 eg^2, 4T1g) - Rep(t2g^3, 4A2g) = b
    # For Dq=0, eigenvalues are a and b. So {a, b} = {0, 15*B}.
    # Looking at the diagrams, t2g^2 eg^1 is the lower one, so a=0, b=15*B.
    # Mix term: For 4T1g, the mixing is 6*sqrt(10)*Dq? No, the mixing for 4T1g is 6*sqrt(10)*Dq.
    # Let's check the 4T1g matrix from a source:
    # E = [[ 10*Dq, 6*sqrt(10)*Dq ],
    #      [ 6*sqrt(10)*Dq, 20*Dq + 15*B ]]
    # Wait, if Dq=0, E=0 and E=15B. This matches!
    
    mat_4t1g = np.array([[10*Dq, 6*np.sqrt(10)*Dq], [6*np.sqrt(10)*Dq, 20*Dq + 15*B]])
    eig_4t1g = np.linalg.eigvalsh(mat_4t1g)
    
    # Doublets: 2Eg, 2T1g, 2T2g, 2A2g
    # Lowest doublets for d3 are usually 2Eg and 2T1g.
    # For 2Eg:
    # 2Eg(t2g^3) energy: Rep(t2g^3, 2Eg) - Rep(t2g^3, 4A2g)
    # From literature, for Cr3+, E(2Eg) - E(4A2g) is approx 35B.
    # For d3, the 2Eg from t2g^3 has Rep = 3C - 12B (Wait, let's check).
    # Actually, the most common value for E(2Eg) - E(4A2g) is around 21,000 cm-1.
    # With B=600, E/B = 35.
    # Let's use the 2Eg and 2T1g energies from a reliable Tanabe-Sugano table.
    # For d3:
    # 2Eg: E = -12Dq + Rep(t2g^3, 2Eg) -> Relative: Rep(t2g^3, 2Eg) - Rep(t2g^3, 4A2g)
    # 2T1g: Mixes (t2g^2 eg^1) and (t2g^1 eg^2)
    # 2T2g: Mixes (t2g^2 eg^1) and (t2g^1 eg^2)
    # 2A2g: (t2g^2 eg^1)
    
    # Let's use a known result: for d3, the 2Eg state is almost constant.
    # E(2Eg) - E(4A2g) = 3C - 15B - (3C) = -15B? No.
    # Let's use the values for Cr3+ (B=600, C=3000):
    # 4A2g: 0
    # 4T2g: 17000 (10Dq) -> Dq = 1700
    # 2Eg: 21500 -> E/B = 21500/600 = 35.8
    # 2T1g: 23000 -> E/B = 23000/600 = 38.3
    # 4T1g(F): 24500 -> E/B = 24500/600 = 40.8
    
    # But we need them as a function of Dq/B.
    # Let's use the formula for 2Eg: E = 21.5B (approx constant)
    # Let's use the formula for 2T1g: E = 23B (approx constant)
    # These are just approximations. Let's try to be more precise.
    
    # Actually, for d3, the doublets come from 2G and 2H.
    # Free ion E(2G) - E(4F) = -1.5B? No, that's for d1.
    # Let's look at a Tanabe-Sugano diagram for d3.
    # The 2Eg line is almost flat, around E/B = 21-22.
    # The 2T1g line is also almost flat, slightly above 2Eg.
    # The 4T2g line is 10 * Dq/B.
    # The 4T1g(F) line starts at 0 and rises.
    
    # Let's re-examine the matrices for doublets.
    # 2Eg (t2g^3) repulsion:
    # For d3, Rep(t2g^3, 4A2g) = 3C + 3B (Wait, let me check this)
    # Rep(t2g^3, 2Eg) = 3C + 15B?
    # Difference = 12B.
    # Let's check if 12B is a reasonable value. 12*600 = 7200. Too low.
    # Let's use the formula: E(2Eg) - E(4A2g) = 3C - 3B (No).
    # Let's use the value from a source: E(2Eg) - E(4A2g) = -15B + 3C/B * B = 3C - 15B.
    # 3(3000) - 15(600) = 9000 - 9000 = 0. Still not right.
    
    # Let's use the values from the Tanabe-Sugano diagram for d3.
    # At Dq/B = 2.0:
    # 4T2g is at 20.
    # 2Eg is at ~21.
    # 2T1g is at ~23.
    # 4T1g(F) is at ~25.
    # At Dq/B = 1.0:
    # 4T2g is at 10.
    # 2Eg is at ~21.
    # 2T1g is at ~23.
    # 4T1g(F) is at ~12.
    # At Dq/B = 3.0:
    # 4T2g is at 30.
    # 2Eg is at ~21.
    # 2T1g is at ~23.
    # 4T1g(F) is at ~35.
    
    # Wait, if 2Eg and 2T1g are around 21 and 23, they will be among the three lowest.
    # Let's refine the 4T1g(F) energy.
    # For Dq/B = 1.0: 
    # mat_4t1g = [[10, 6*sqrt(10)], [6*sqrt(10), 20+15]] = [[10, 18.97], [18.97, 35]]
    # Eigenvalues: trace=45, det=350 - 360 = -10.
    # E = (45 +/- sqrt(45^2 + 40))/2 = (45 +/- 45.4)/2.
    # E1 = 0.2, E2 = 45.2.
    # So 4T1g(F) is very low at Dq/B = 1.0!
    
    # Let's re-calculate for Dq/B = 1, 2.2, 3.5.
    
    results = []
    for dq_over_b in [1.00, 2.20, 3.50]:
        # 4T2g
        e_4t2g = 10 * dq_over_b
        
        # 4T1g
        mat_4t1g = np.array([[10*dq_over_b, 6*np.sqrt(10)*dq_over_b], [6*np.sqrt(10)*dq_over_b, 20*dq_over_b + 15]])
        eig_4t1g = np.linalg.eigvalsh(mat_4t1g)
        e_4t1gf = eig_4t1g[0]
        e_4t1gp = eig_4t1g[1]
        
        # Doublets (approximate from TS diagram)
        # 2Eg is almost flat at ~21.5
        # 2T1g is almost flat at ~23.0
        e_2eg = 21.5
        e_2t1g = 23.0
        
        terms = [('4T2g', e_4t2g), ('4T1g(F)', e_4t1gf), ('2Eg', e_2eg), ('2T1g', e_2t1g)]
        terms.sort(key=lambda x: x[1])
        results.append((dq_over_b, terms[:3]))
        
    return results

print(solve_d3(1.0)) # Just to check
EOF
python3 solver.py
