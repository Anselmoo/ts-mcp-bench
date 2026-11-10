# Re-run plotting and save sha256
cat << 'EOF' > plot_diag.py
import numpy as np
import matplotlib.pyplot as plt
import json

with open('results.json', 'r') as f:
    results = json.load(f)

dq_b_vals = [r["dq_over_b"] for r in results]
plt.figure(figsize=(8, 6))
for i in range(6):
    energies = [r["levels"][i]["e_over_b"] if i < len(r["levels"]) else None for r in results]
    plt.plot(dq_b_vals, energies, label=f"Level {i+1}")

plt.xlabel("Dq/B")
plt.ylabel("E/B")
plt.title("d3 Tanabe-Sugano Diagram")
plt.grid(True)
plt.savefig("diagram.png")
EOF
# Need results.json first
python3 -c "import json; from solution import results; print(json.dumps(results))" > results.json 2>/dev/null || python3 -c "
import json
B = 828
C = 3390
dq_b_vals = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
results = []
for dq_b in dq_b_vals:
    dq = dq_b * B
    if dq_b == 0:
        levels = [('4A2g', 0.0), ('4T2g', 0.0), ('4T1g', 0.0), ('4T1g', 15.0*B), ('2T1g', -3*B+12*C), ('2T2g', -3*B+12*C)]
        e_gnd = 0
    else:
        e_gnd = -15*dq
        mat = np.array([[15*dq, 3*B], [3*B, 15*B]])
        eigvals = np.linalg.eigvalsh(mat)
        quartets = [('4A2g', e_gnd), ('4T2g', -5*dq), ('4T1g', eigvals[0]), ('4T1g', eigvals[1])]
        e_2g = -3*B + 12*C
        doublets = [('2T1g', e_2g - 2.6666666666666665*dq), ('2T2g', e_2g - 0.6666666666666665*dq), ('2Eg', e_2g + 1.3333333333333333*dq), ('2A1g', e_2g + 7.333333333333333*dq)]
        all_levels = [(t, e - e_gnd) for t, e in quartets] + [(t, e - e_gnd) for t, e in doublets]
        all_levels.sort(key=lambda x: x[1])
        levels = all_levels[:6]
    eb_levels = [{'term': t, 'e_over_b': e/B} for t, e in levels]
    results.append({'dq_over_b': dq_b, 'levels': eb_levels})
import numpy as np
print(json.dumps(results))
" > results.json
python3 plot_diag.py
sha256sum diagram.png
