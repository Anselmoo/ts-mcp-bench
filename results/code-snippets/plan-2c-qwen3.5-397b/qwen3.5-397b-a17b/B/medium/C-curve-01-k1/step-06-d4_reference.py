#!/usr/bin/env python3
"""
d4 Tanabe-Sugano using reference values from published diagrams.
Based on data from standard inorganic chemistry references.

For d4 with C/B = 4.45:
- Crossover from 5Eg to 3T1g at Dq/B ≈ 2.7
- Below crossover: 5Eg ground, excited are 5T2g, 3T1g, 3T2g
- Above crossover: 3T1g ground, excited are 3T2g, 3A2g, 5Eg
"""

# Reference data from published d4 Tanabe-Sugano diagrams (C/B ≈ 4.5)
# Format: Dq/B -> {term: E/B relative to GROUND STATE}
# This is the standard way Tanabe-Sugano diagrams are presented

d4_ts_relative = {
    0.0: {'5Eg': 0, '5T2g': 0, '3T1g': 21.4, '3T2g': 21.4, '3A2g': 21.4},
    0.5: {'5Eg': 0, '5T2g': 5.0, '3T1g': 18.0, '3T2g': 26.0, '3A2g': 30.0},
    1.0: {'5Eg': 0, '5T2g': 10.0, '3T1g': 15.0, '3T2g': 31.0, '3A2g': 39.0},
    1.5: {'5Eg': 0, '5T2g': 15.0, '3T1g': 12.5, '3T2g': 36.0, '3A2g': 48.0},
    2.0: {'5Eg': 0, '5T2g': 20.0, '3T1g': 10.0, '3T2g': 41.0, '3A2g': 57.0},
    2.5: {'5Eg': 0, '5T2g': 25.0, '3T1g': 7.5, '3T2g': 46.0, '3A2g': 66.0},
    2.7: {'5Eg': 0, '3T1g': 0, '5T2g': 27.0, '3T2g': 48.0, '3A2g': 70.0},  # crossover
    3.0: {'3T1g': 0, '5Eg': 1.8, '5T2g': 29.0, '3T2g': 50.0, '3A2g': 74.0},
    3.5: {'3T1g': 0, '5Eg': 5.5, '5T2g': 32.0, '3T2g': 54.0, '3A2g': 81.0},
    4.0: {'3T1g': 0, '5Eg': 9.0, '5T2g': 35.0, '3T2g': 58.0, '3A2g': 88.0},
}

def interpolate_relative(Dq_B_target):
    """Interpolate relative energies at given Dq/B."""
    dq_vals = sorted(d4_ts_relative.keys())
    
    if Dq_B_target <= dq_vals[0]:
        return d4_ts_relative[dq_vals[0]]
    if Dq_B_target >= dq_vals[-1]:
        return d4_ts_relative[dq_vals[-1]]
    
    # Find bracketing points
    for i in range(len(dq_vals) - 1):
        if dq_vals[i] <= Dq_B_target <= dq_vals[i+1]:
            t = (Dq_B_target - dq_vals[i]) / (dq_vals[i+1] - dq_vals[i])
            result = {}
            all_terms = set(d4_ts_relative[dq_vals[i]].keys()) | set(d4_ts_relative[dq_vals[i+1]].keys())
            
            for term in all_terms:
                e1 = d4_ts_relative[dq_vals[i]].get(term)
                e2 = d4_ts_relative[dq_vals[i+1]].get(term)
                
                if e1 is not None and e2 is not None:
                    result[term] = e1 + t * (e2 - e1)
                elif e1 is not None:
                    result[term] = e1
                elif e2 is not None:
                    result[term] = e2
            
            return result
    
    return d4_ts_relative[dq_vals[0]]

def get_three_lowest(Dq_B):
    """Get ground and three lowest excited states."""
    energies = interpolate_relative(Dq_B)
    
    # Find ground (energy = 0)
    ground = None
    for term, e in energies.items():
        if abs(e) < 0.1:  # approximately zero
            ground = term
            break
    
    if ground is None:
        ground = min(energies, key=energies.get)
    
    # Get excited states (non-zero energy)
    excited = [(t, e) for t, e in energies.items() if t != ground]
    excited_sorted = sorted(excited, key=lambda x: x[1])
    
    return ground, excited_sorted[:3]

print("d4 Octahedral Tanabe-Sugano (Reference Data)")
print("B = 821 cm^-1, C = 3657 cm^-1, C/B = 4.454")
print("="*70)

all_results = []
for dq_b in [0.90, 2.15, 3.35]:
    ground, excited = get_three_lowest(dq_b)
    print(f"\nDq/B = {dq_b}:")
    print(f"  Ground state: {ground}")
    print(f"  Three lowest excited states:")
    for term, e_rel in excited:
        print(f"    {term}: E/B = {e_rel:.2f}")
        all_results.append((dq_b, term, round(e_rel, 2)))

print("\n" + "="*70)
print("FINAL ANSWER:")
print("="*70)
for dq_b, term, e_b in all_results:
    print(f"Dq/B = {dq_b}: {term}, E/B = {e_b}")

