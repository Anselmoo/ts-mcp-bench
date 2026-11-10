cat << 'EOF' > solution.py
import numpy as np
import matplotlib.pyplot as plt

def get_abs_energy(term, x):
    if term == '4T1g(F)': return 7.5 - np.sqrt((7.5 + 10*x)**2 + 120)
    if term == '4T2g': return 0
    if term == '4Ag': return 10*x
    if term == '4T1g(P)': return 7.5 + np.sqrt((7.5 + 10*x)**2 + 120)
    if term == '2Eg': return 10 - 18*x
    if term == '2T1g': return 15 - 10*x
    return 100

x_values = np.arange(0, 4.1, 0.5)
all_terms = ['4T1g(F)', '4T2g', '4Ag', '4T1g(P)', '2Eg', '2T1g']

plt.figure(figsize=(8, 6))
for term in all_terms:
    abs_energies = [get_abs_energy(term, x) for x in x_values]
    # Shift by the ground state at each x
    rel_energies = []
    for i in range(len(x_values)):
        gs = min([get_abs_energy(t, x_values[i]) for t in all_terms])
        rel_energies.append(abs_energies[i] - gs)
    plt.plot(x_values, rel_energies, label=term)

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.legend()
plt.title('Tanabe-Sugano Diagram for d7')
plt.savefig('diagram.png')
EOF
python3 solution.py
sha256sum diagram.png
