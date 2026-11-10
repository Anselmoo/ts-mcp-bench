python3 -c "
# Given data for low-spin d6 octahedral complex
nu1 = 16700  # cm^-1, first band (1A1g -> 1T1g from t2g5eg1)
nu2 = 26330  # cm^-1, second band (1A1g -> 1T2g from t2g5eg1)
nu3 = 35020  # cm^-1, third band (1A1g -> 1T1g from t2g4eg2)

# For low-spin d6 octahedral, the energy expressions are:
# nu1 = 10Dq - C
# nu2 = 10Dq + 16B - C
# With C/B = 4.0, so C = 4B
# nu1 = 10Dq - 4B
# nu2 = 10Dq + 12B

# Difference gives: nu2 - nu1 = 16B
B = (nu2 - nu1) / 16

# From nu1: 10Dq = nu1 + 4B
Dq = (nu1 + 4*B) / 10

# Verify with nu2
nu2_calc = 10*Dq + 12*B

# Predict nu3 (from t2g4eg2 configuration, approximately 20Dq - C)
nu3_pred = 20*Dq - 4*B

print(f'B = {B:.3f} cm^-1')
print(f'Dq = {Dq:.3f} cm^-1')
print(f'10Dq = {10*Dq:.3f} cm^-1')
print(f'nu2 calculated = {nu2_calc:.3f} cm^-1 (observed: {nu2})')
print(f'nu3 predicted = {nu3_pred:.3f} cm^-1 (observed: {nu3})')
print(f'nu3 deviation = {nu3_pred - nu3:.3f} cm^-1')
"
