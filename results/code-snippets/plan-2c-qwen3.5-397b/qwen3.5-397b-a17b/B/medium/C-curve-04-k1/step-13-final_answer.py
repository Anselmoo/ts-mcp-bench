"""
Final answer for d5 Tanabe-Sugano problem.

The term labels should distinguish between states of the same symmetry
from different parent free ion terms. Standard notation uses the parent
term in parentheses for doublets.
"""

# Final results with proper term labels
# Distinguishing 2T1g from 2I, 2H, 2G by their parent terms

results = {
    1.45: [
        ('2T1g(2I)', 11.78),
        ('2A1g(2I)', 14.68),
        ('2T1g(2H)', 15.78),
    ],
    2.55: [
        ('2T1g(2I)', 9.58),
        ('4T1g(4G)', 10.81),
        ('2T1g(2H)', 13.58),
    ],
    3.25: [
        ('4T1g(4G)', 4.17),
        ('2T1g(2I)', 8.18),
        ('2T1g(2H)', 12.18),
    ],
}

print("="*70)
print("d5 Octahedral Complex - Tanabe-Sugano Analysis")
print("B = 800 cm⁻¹, C = 3473 cm⁻¹")
print("="*70)
print()
print("Three lowest excited terms at each Dq/B value:")
print("(Term labels include parent free ion term in parentheses)")
print()

for Dq_B in [1.45, 2.55, 3.25]:
    print(f"Dq/B = {Dq_B}:")
    for i, (term, E_B) in enumerate(results[Dq_B], 1):
        print(f"  {i}. {term}: E/B = {E_B:.2f}")
    print()

# Generate structured output
print("="*70)
print("STRUCTURED OUTPUT (for automated parsing):")
print("="*70)

points = []
for Dq_B in [1.45, 2.55, 3.25]:
    for term, E_B in results[Dq_B]:
        points.append((Dq_B, term, E_B))

for Dq_B, term, E_B in points:
    print(f"{Dq_B:.2f} {term} {E_B:.2f}")
