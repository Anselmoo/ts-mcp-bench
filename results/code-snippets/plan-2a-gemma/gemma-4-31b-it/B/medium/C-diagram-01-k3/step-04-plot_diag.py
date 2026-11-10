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
