python3 << 'EOF'
# For d6 low-spin octahedral complex [Co(oxalate)3]3-
# Ground state: 1A1g (t2g6)
# Excited states: 1T1g and 1T2g (from t2g5eg1)

# Energy expressions (from ligand-field theory for d6 low-spin):
# ν1(1T1g) = 10Dq - 3B + C
# ν2(1T2g) = 10Dq + 7B + C

# Given data
nu1 = 16611  # cm^-1 (1T1g)
nu2 = 23529  # cm^-1 (1T2g)
C_over_B = 4.5

# With C = 4.5B:
# ν1 = 10Dq - 3B + 4.5B = 10Dq + 1.5B
# ν2 = 10Dq + 7B + 4.5B = 10Dq + 11.5B

# Subtracting: ν2 - ν1 = 10B
B = (nu2 - nu1) / 10

# Then: 10Dq = ν1 - 1.5B
Dq = (nu1 - 1.5 * B) / 10

C = C_over_B * B

print(f"B = {B:.1f} cm^-1")
print(f"Dq = {Dq:.1f} cm^-1")
print(f"C = {C:.1f} cm^-1")
print(f"C/B = {C/B:.2f}")

# Verification
nu1_calc = 10*Dq - 3*B + C
nu2_calc = 10*Dq + 7*B + C
print(f"\nVerification:")
print(f"ν1 calculated: {nu1_calc:.1f} cm^-1 (given: {nu1} cm^-1)")
print(f"ν2 calculated: {nu2_calc:.1f} cm^-1 (given: {nu2} cm^-1)")
EOF