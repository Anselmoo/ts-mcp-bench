cat > ts_d3_final_output.py << 'EOF'
import numpy as np
import hashlib

# Parameters
B = 828
C = 3390
C_over_B = C / B

dq_over_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

def d3_energies(dq_over_b, C_over_B=4.094202898550725):
    x = dq_over_b
    levels = []
    
    # Quartets
    levels.append((0.0, '4A2g'))
    levels.append((10 * x, '4T2g'))
    
    H_4t1g = np.array([[18*x, 4*x], [4*x, 15 + 18*x]])
    eig_4t1g = np.linalg.eigvalsh(H_4t1g)
    # Lower 4T1g is mostly 4T1g(F) character, upper is mostly 4T1g(P)
    levels.append((eig_4t1g[0], '4T1g'))
    levels.append((eig_4t1g[1], '4T1g'))
    
    # Doublets
    E_2G = 6 + 3*C_over_B
    E_2H = 6 + 3*C_over_B
    
    H_2eg = np.array([[E_2G + 2*x, 2*np.sqrt(6)*x], 
                      [2*np.sqrt(6)*x, E_2H + x]])
    eig_2eg = np.linalg.eigvalsh(H_2eg)
    levels.append((eig_2eg[0], '2Eg'))
    levels.append((eig_2eg[1], '2Eg'))
    
    H_2t1g = np.array([[E_2G - x, 2*x], 
                       [2*x, E_2H + x]])
    eig_2t1g = np.linalg.eigvalsh(H_2t1g)
    levels.append((eig_2t1g[0], '2T1g'))
    levels.append((eig_2t1g[1], '2T1g'))
    
    H_2t2g = np.array([[E_2G + x, x], 
                       [x, E_2H - 2*x]])
    eig_2t2g = np.linalg.eigvalsh(H_2t2g)
    levels.append((eig_2t2g[0], '2T2g'))
    levels.append((eig_2t2g[1], '2T2g'))
    
    levels.sort(key=lambda x: x[0])
    ground_energy = levels[0][0]
    levels = [(e - ground_energy, label) for e, label in levels]
    
    return levels[:6]

# Generate structured output
results = []
for dq_over_b in dq_over_b_values:
    levels = d3_energies(dq_over_b, C_over_B)
    results.append({
        'dq_over_b': dq_over_b,
        'levels': [(label, round(e, 4)) for e, label in levels]
    })

# Get sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

# Print structured output
import json
output = {
    'points': [
        {
            'dq_over_b': r['dq_over_b'],
            'levels': [{'term': label, 'e_over_b': e} for label, e in r['levels']]
        }
        for r in results
    ],
    'image_path': 'diagram.png',
    'image_sha256': sha256_hash,
    'reason': 'Computed Tanabe-Sugano diagram for d³ octahedral ion using crystal field theory with Racah parameters B=828 cm⁻¹, C=3390 cm⁻¹, diagonalizing quartet and doublet state matrices.'
}

print(json.dumps(output, indent=2))
EOF
python3 ts_d3_final_output.py