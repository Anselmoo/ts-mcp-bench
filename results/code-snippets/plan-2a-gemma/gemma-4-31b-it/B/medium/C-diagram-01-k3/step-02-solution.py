import numpy as np
import matplotlib.pyplot as plt

B = 828
C = 3390
dq_b_vals = np.arange(0, 4.5, 0.5)

results = []

for dq_b in dq_b_vals:
    dq = dq_b * B
    
    # Quartets
    # E(4A2g) = -15*dq
    # E(4T2g) = -5*dq
    # 4T1g mixing
    mat = np.array([[15*dq, 3*B], [3*B, 15*B]])
    eigvals = np.linalg.eigvalsh(mat)
    
    # Ground state: 4A2g
    e_gnd = -15*dq
    
    quartets = [
        ("4A2g", -15*dq),
        ("4T2g", -5*dq),
        ("4T1g", eigvals[0]),
        ("4T1g", eigvals[1])
    ]
    
    # Doublets from 2G
    e_2g = -3*B + 12*C
    # Normalized shifts for 2G -> A1, E, T1, T2
    # shifts = [6, 0, -4, -2] -> sum = -12. 
    # Normalized: shifts + 12/9 = [7.33, 1.33, -2.67, -0.67]
    doublets_2g = [
        ("2T1g", e_2g - 2.6666666666666665 * dq),
        ("2T2g", e_2g - 0.6666666666666665 * dq),
        ("2Eg", e_2g + 1.3333333333333333 * dq),
        ("2A1g", e_2g + 7.333333333333333 * dq)
    ]
    
    # All levels relative to 4A2g
    all_levels = []
    for term, e in quartets:
        all_levels.append((term, e - e_gnd))
    for term, e in doublets_2g:
        all_levels.append((term, e - e_gnd))
        
    # Sort by energy
    all_levels.sort(key=lambda x: x[1])
    
    # Lowest 6
    lowest_6 = all_levels[:6]
    
    # E/B
    eb_levels = []
    for term, e in lowest_6:
        eb_levels.append({"term": term, "e_over_b": e / B})
        
    results.append({"dq_over_b": dq_b, "levels": eb_levels})

# Plotting
plt.figure(figsize=(8, 6))
for term_idx in range(6):
    energies = [r["levels"][term_idx]["e_over_b"] for r in results]
    plt.plot(dq_b_vals, energies, label=f"Level {term_idx+1}")

plt.xlabel("Dq/B")
plt.ylabel("E/B")
plt.title("d3 Tanabe-Sugano Diagram (Approx)")
plt.grid(True)
plt.savefig("diagram.png")

import json
print(json.dumps(results))
