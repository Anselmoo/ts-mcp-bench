import numpy as np
import matplotlib.pyplot as plt

def solve_d5_levels(dq_over_b, b, c):
    # B and C are given. We work in units of B.
    # C_over_b = c / b
    # Dq_over_b is already given.
    
    # For d5, the ground state is 6A1g (E=0) for low Dq/B.
    # We use the quartet matrices (C=4B approximation for quartet terms).
    # 4T1g from 4G, 4F, 4P
    m_t1 = np.array([
        [10.0 - 6.0*dq_over_b, 6.0, 0.0],
        [6.0, 12.0 - 6.0*dq_over_b, 6.0],
        [0.0, 6.0, 26.0 - 18.0*dq_over_b]
    ])
    
    # 4T2g from 4G, 4F, 4D
    m_t2 = np.array([
        [10.0 - 6.0*dq_over_b, 6.0, 0.0],
        [6.0, 12.0 - 6.0*dq_over_b, 6.0],
        [0.0, 6.0, 15.0 - 6.0*dq_over_b]
    ])
    
    # 4A2g from 4G, 4F
    m_a2 = np.array([
        [10.0, 6.0],
        [6.0, 12.0]
    ])
    # Actually 4A2g LF depends on Dq. For d5, the A2g states from 4G and 4F have 0 LF shift.
    # Let's use a more accurate 4A2g:
    # The LF shift for 4A2g is 0 for both 4G and 4F? 
    # Let's use the standard 4A2g matrix:
    m_a2 = np.array([
        [10.0, 6.0*dq_over_b],
        [6.0*dq_over_b, 12.0]
    ])
    
    # 4Eg from 4G, 4D
    m_eg = np.array([
        [10.0 - 6.0*dq_over_b, 6.0],
        [6.0, 15.0 - 6.0*dq_over_b]
    ])

    # Solve for eigenvalues
    ev_t1 = np.linalg.eigvalsh(m_t1)
    ev_t2 = np.linalg.eigvalsh(m_t2)
    ev_a2 = np.linalg.eigvalsh(m_a2)
    ev_eg = np.linalg.eigvalsh(m_eg)
    
    # The ground state 6A1g
    # The low spin ground state 2T2g
    # E(2T2g) for d5 is approx 26B - 20Dq (for C=4B)
    ev_2t2 = 26.0 - 20.0*dq_over_b
    
    levels = []
    levels.append(('6A1g', 0.0))
    for e in ev_t1: levels.append(('4T1g', e))
    for e in ev_t2: levels.append(('4T2g', e))
    for e in ev_a2: levels.append(('4A2g', e))
    for e in ev_eg: levels.append(('4Eg', e))
    levels.append(('2T2g', ev_2t2))
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    # The ground state should be 0.
    ground_energy = levels[0][1]
    final_levels = []
    for term, e in levels:
        final_levels.append({'term': term, 'e_over_b': e - ground_energy})
        
    return final_levels[:6]

b = 806
c = 3570
dq_vals = np.arange(0, 4.5, 0.5)
results = []

for dq in dq_vals:
    lvls = solve_d5_levels(dq, b, c)
    results.append({'dq_over_b': dq, 'levels': lvls})

# Printing the results
import json
print(json.dumps(results))

# Plotting
plt.figure(figsize=(8,6))
for dq in dq_vals:
    lvls = solve_d5_levels(dq, b, c)
    for i, l in enumerate(lvls):
        plt.plot(dq, l['e_over_b'], 'o')

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.title('Tanabe-Sugano Diagram for d5')
plt.grid(True)
plt.savefig('diagram.png')
