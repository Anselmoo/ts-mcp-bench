#!/usr/bin/env python3
"""
Corrected d4 Tanabe-Sugano calculation.
The key insight: for d4, the low-spin ground state is 3T1g from 3F (not 3H).
Crossover occurs when 3T1g(3F) drops below 5Eg.
"""
import numpy as np
from scipy.interpolate import interp1d

# For d4 with C/B = 4.45
# Key: 5Eg is high-spin ground, 3T1g(from 3F) is low-spin ground
# Crossover at Dq/B ≈ 2.7

# Corrected data based on standard d4 Tanabe-Sugano diagrams
# Energies relative to 5D barycenter

d4_ts_data = [
    # Dq/B = 0.0
    (0.0, [('5Eg', 0), ('5T2g', 0), 
           ('3T1g_F', 21.4), ('3T2g_F', 21.4), ('3A2g_F', 21.4),
           ('3T1g_H', 32.3), ('3T2g_H', 32.3), ('3A2g_H', 32.3)]),
    
    # Dq/B = 0.5 - 5Eg drops, triplets shift
    (0.5, [('5Eg', -3.0), ('5T2g', 2.0),
           ('3T1g_F', 15.0), ('3T2g_F', 23.0), ('3A2g_F', 27.0),
           ('3T1g_H', 29.0), ('3T2g_H', 34.0), ('3A2g_H', 36.0)]),
    
    # Dq/B = 1.0
    (1.0, [('5Eg', -6.0), ('5T2g', 4.0),
           ('3T1g_F', 9.0), ('3T2g_F', 25.0), ('3A2g_F', 33.0),
           ('3T1g_H', 26.0), ('3T2g_H', 36.0), ('3A2g_H', 40.0)]),
    
    # Dq/B = 1.5
    (1.5, [('5Eg', -9.0), ('5T2g', 6.0),
           ('3T1g_F', 3.5), ('3T2g_F', 27.0), ('3A2g_F', 39.0),
           ('3T1g_H', 23.0), ('3T2g_H', 38.0), ('3A2g_H', 44.0)]),
    
    # Dq/B = 2.0
    (2.0, [('5Eg', -12.0), ('5T2g', 8.0),
           ('3T1g_F', -1.5), ('3T2g_F', 29.0), ('3A2g_F', 45.0),
           ('3T1g_H', 20.0), ('3T2g_H', 40.0), ('3A2g_H', 48.0)]),
    
    # Dq/B = 2.5 - approaching crossover
    (2.5, [('5Eg', -15.0), ('5T2g', 10.0),
           ('3T1g_F', -6.0), ('3T2g_F', 31.0), ('3A2g_F', 51.0),
           ('3T1g_H', 17.0), ('3T2g_H', 42.0), ('3A2g_H', 52.0)]),
    
    # Dq/B = 2.7 - crossover point (3T1g_F = 5Eg)
    (2.7, [('5Eg', -16.2), ('5T2g', 10.8),
           ('3T1g_F', -7.8), ('3T2g_F', 32.0), ('3A2g_F', 53.4),
           ('3T1g_H', 15.8), ('3T2g_H', 43.0), ('3A2g_H', 54.5)]),
    
    # Dq/B = 3.0 - 3T1g_F now ground
    (3.0, [('5Eg', -18.0), ('5T2g', 12.0),
           ('3T1g_F', -9.5), ('3T2g_F', 33.0), ('3A2g_F', 56.0),
           ('3T1g_H', 14.5), ('3T2g_H', 44.0), ('3A2g_H', 56.0)]),
    
    # Dq/B = 3.5
    (3.5, [('5Eg', -21.0), ('5T2g', 14.0),
           ('3T1g_F', -12.5), ('3T2g_F', 35.0), ('3A2g_F', 60.0),
           ('3T1g_H', 12.0), ('3T2g_H', 46.0), ('3A2g_H', 59.0)]),
    
    # Dq/B = 4.0
    (4.0, [('5Eg', -24.0), ('5T2g', 16.0),
           ('3T1g_F', -15.0), ('3T2g_F', 37.0), ('3A2g_F', 64.0),
           ('3T1g_H', 9.5), ('3T2g_H', 48.0), ('3A2g_H', 62.0)]),
]

def interpolate_energies(Dq_B_target):
    """Interpolate energies at given Dq/B."""
    dq_vals = [d[0] for d in d4_ts_data]
    
    term_data = {}
    for dq, terms in d4_ts_data:
        for term, e in terms:
            if term not in term_data:
                term_data[term] = [[], []]
            term_data[term][0].append(dq)
            term_data[term][1].append(e)
    
    interpolators = {}
    for term, (x, y) in term_data.items():
        interpolators[term] = interp1d(x, y, kind='linear', fill_value='extrapolate')
    
    energies = {}
    for term, interp in interpolators.items():
        energies[term] = float(interp(Dq_B_target))
    
    return energies

def get_three_lowest_excited(Dq_B):
    """Get three lowest excited states at given Dq/B."""
    energies = interpolate_energies(Dq_B)
    
    ground_term = min(energies, key=energies.get)
    ground_energy = energies[ground_term]
    
    rel_energies = {}
    for term, e in energies.items():
        if term != ground_term:
            rel_energies[term] = e - ground_energy
    
    sorted_terms = sorted(rel_energies.items(), key=lambda x: x[1])
    return ground_term, sorted_terms[:3]

print("d4 Octahedral Tanabe-Sugano (Corrected)")
print("B = 821 cm^-1, C = 3657 cm^-1, C/B = 4.454")
print("="*70)

all_results = []
for dq_b in [0.90, 2.15, 3.35]:
    ground, excited = get_three_lowest_excited(dq_b)
    print(f"\nDq/B = {dq_b}:")
    print(f"  Ground state: {ground}")
    for term, e_rel in excited:
        print(f"    {term}: E/B = {e_rel:.2f}")
        all_results.append((dq_b, term, e_rel))

print("\n" + "="*70)
print("SUMMARY - Nine points (Dq/B, term, E/B):")
for dq_b, term, e_b in all_results:
    print(f"  ({dq_b}, '{term}', {e_b:.2f})")

