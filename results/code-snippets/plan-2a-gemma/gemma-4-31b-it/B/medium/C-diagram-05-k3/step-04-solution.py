import numpy as np
import matplotlib.pyplot as plt

def compute_levels(x):
    # x = Dq/B
    val = np.sqrt((7.5 + 10*x)**2 + 120)
    e_4t1g_f = 7.5 - val
    e_4t1g_p = 7.5 + val
    e_4t2g = 0
    e_4ag = 10*x
    
    # Refined doublet energies
    e_2eg = 10 - 18*x
    e_2t1g = 15 - 10*x
    e_2t2g = 20 - 5*x
    
    levels = [
        ('4T1g(F)', e_4t1g_f),
        ('4T2g', e_4t2g),
        ('4Ag', e_4ag),
        ('4T1g(P)', e_4t1g_p),
        ('2Eg', e_2eg),
        ('2T1g', e_2t1g)
    ]
    
    levels.sort(key=lambda x: x[1])
    ground_e = levels[0][1]
    relative_levels = []
    for term, e in levels:
        relative_levels.append((term, e - ground_e))
        
    return relative_levels

x_values = np.arange(0, 4.1, 0.5)
for x in x_values:
    levels = compute_levels(x)
    print(f"{x:.1f}")
    for term, e in levels:
        print(f"{term} {e:.3f}")

# Plotting
plt.figure(figsize=(8, 6))
all_terms = ['4T1g(F)', '4T2g', '4Ag', '4T1g(P)', '2Eg', '2T1g']
for term in all_terms:
    energies = []
    for x in x_values:
        levels = compute_levels(x)
        for t, e in levels:
            if t == term:
                energies.append(e)
                break
    # Need to shift them relative to ground state at each x
    # This is tricky for plotting. Let's plot absolute energies then shift.
    pass

# To plot correctly, I'll compute absolute energies
for term in all_terms:
    abs_energies = []
    for x in x_values:
        # Redefine the energy based on the term
        if term == '4T1g(F)': e = 7.5 - np.sqrt((7.5 + 10*x)**2 + 120)
        elif term == '4T2g': e = 0
        elif term == '4Ag': e = 10*x
        elif term == '4T1g(P)': e = 7.5 + np.sqrt((7.5 + 10*x)**2 + 120)
        elif term == '2Eg': e = 10 - 18*x
        elif term == '2T1g': e = 15 - 10*x
        abs_energies.append(e)
    
    # Shift by the ground state at each x
    # The ground state is min(abs_energies[i])
    # Wait, just compute ground state for each x
    
plt.close() # Just for now
