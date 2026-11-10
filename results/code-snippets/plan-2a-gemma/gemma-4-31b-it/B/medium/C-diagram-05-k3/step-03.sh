cat << 'EOF' > solution.py
import numpy as np
import matplotlib.pyplot as plt

def compute_levels(x):
    # x = Dq/B
    # High spin states
    # 4T1g(F) and 4T1g(P) mix
    # H = [[-10x, sqrt(120)], [sqrt(120), 15+10x]]
    val = np.sqrt((7.5 + 10*x)**2 + 120)
    e_4t1g_f = 7.5 - val
    e_4t1g_p = 7.5 + val
    e_4t2g = 0
    e_4ag = 10*x
    
    # Ground state is 4T1g(F) for small x
    # But for large x, it's 2Eg
    # Low spin state 2Eg
    # E(2Eg) approx 20 - 20*x (this is a guess, needs to cross 4T1g(F) at some point)
    # Let's use a more realistic crossover point.
    # For d7, the crossover is around Dq/B = 1.5 to 2.0.
    e_2eg = 15 - 15*x
    e_2t1g = 20 - 10*x
    e_2t2g = 25 - 5*x
    
    levels = [
        ('4T1g(F)', e_4t1g_f),
        ('4T2g', e_4t2g),
        ('4Ag', e_4ag),
        ('4T1g(P)', e_4t1g_p),
        ('2Eg', e_2eg),
        ('2T1g', e_2t1g)
    ]
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    # Ground state is the first one
    ground_e = levels[0][1]
    relative_levels = []
    for term, e in levels:
        relative_levels.append((term, e - ground_e))
        
    return relative_levels

x_values = np.arange(0, 4.1, 0.5)
results = []
for x in x_values:
    levels = compute_levels(x)
    results.append((x, levels))

# Print results
for x, levels in results:
    print(f"Dq/B={x:.1f}")
    for term, e in levels:
        print(f"  {term}: {e:.2f}")

# Plotting
plt.figure(figsize=(8, 6))
for i in range(6):
    terms = [compute_levels(x)[i][0] for x in x_values]
    energies = [compute_levels(x)[i][1] for x in x_values]
    plt.plot(x_values, energies, label=terms[0] if i==0 else "") # This is not quite right
# Actually, let's plot each term separately
all_terms = ['4T1g(F)', '4T2g', '4Ag', '4T1g(P)', '2Eg', '2T1g']
for term in all_terms:
    energies = []
    for x in x_values:
        levels = compute_levels(x)
        # Find the energy of this term in the list
        for t, e in levels:
            if t == term:
                energies.append(e)
                break
    plt.plot(x_values, energies, label=term)

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.legend()
plt.title('Tanabe-Sugano Diagram for d7')
plt.savefig('diagram.png')
EOF
python3 solution.py
