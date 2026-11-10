# For tetrahedral d8 (Ni2+), ground state is 3A2
# First transition: 3A2 -> 3T2 at energy = 10Dq
# Second transition given: 3A2 -> 3T1(2) (the higher 3T1 state)

# The 3T1 states come from mixing of 3T1(F) and 3T1(P)
# Energy matrix for 3T1 states:
# | 18Dq      4Dq     |
# | 4Dq    15B + 6Dq  |

# Characteristic equation: E^2 - E(24Dq + 15B) + (200Dq^2 + 90BDq) = 0

# Given data
E_T2 = 4400  # cm^-1, assigned to 3T2
E_T1_high = 15500  # cm^-1, assigned to 3T1(2)

# From 3T2: E = 10Dq
Dq = E_T2 / 10
print(f"Dq = {Dq} cm^-1")

# For the 3T1(2) state (higher energy root), solve the quadratic
# E^2 - E(24Dq + 15B) + (200Dq^2 + 90BDq) = 0
# Rearranging to solve for B:
# E^2 - 24Dq*E - 15B*E + 200Dq^2 + 90BDq = 0
# E^2 - 24Dq*E + 200Dq^2 = B(15E - 90Dq)
# B = (E^2 - 24Dq*E + 200Dq^2) / (15E - 90Dq)

E = E_T1_high
numerator = E**2 - 24*Dq*E + 200*Dq**2
denominator = 15*E - 90*Dq
B = numerator / denominator

print(f"B = {B:.1f} cm^-1")

# Verify by calculating both 3T1 energies
a = 1
b = -(24*Dq + 15*B)
c = 200*Dq**2 + 90*B*Dq

E1 = (-b - (b**2 - 4*a*c)**0.5) / (2*a)  # Lower 3T1(1)
E2 = (-b + (b**2 - 4*a*c)**0.5) / (2*a)  # Higher 3T1(2)

print(f"\nVerification:")
print(f"3T2 energy: {10*Dq} cm^-1 (observed: {E_T2})")
print(f"3T1(1) energy: {E1:.1f} cm^-1")
print(f"3T1(2) energy: {E2:.1f} cm^-1 (observed: {E_T1_high})")

# Check C/B ratio (given as 4.5, not needed for this calculation)
C_over_B = 4.5
C = C_over_B * B
print(f"\nC = {C:.1f} cm^-1 (using C/B = 4.5)")
