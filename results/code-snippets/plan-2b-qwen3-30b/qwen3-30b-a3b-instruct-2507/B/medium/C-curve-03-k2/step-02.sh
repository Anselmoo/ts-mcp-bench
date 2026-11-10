cat > ligand_field_analysis.py << 'EOF'
# Python script to compute ligand field energies for d7 octahedral complexes

# Constants
B = 784  # cm^-1
C = 3699  # cm^-1

# Dq/B values to analyze
dq_over_b_values = [1.45, 2.45, 3.00]

# Term symbols for d7 octahedral: 4T1g, 4T2g, 4A2g, 2Eg, 2T1g, 2T2g, 2A1g, 2T1g (excited), etc.
# Ground term is 4T1g
# We need energies of the three lowest excited terms relative to 4T1g

# Energy expressions for d7 octahedral terms (in cm^-1, then convert to E/B)
# Standard ligand field theory for d7:
# 4T1g (ground) - 0
# 4T2g - Dq
# 4A2g - 2Dq
# 2Eg - 2Dq + 2B
# 2T1g - 3Dq + 2B
# 2T2g - 3Dq + 3B
# 2A1g - 4Dq + 2B

# But note: for d7, the 4T1g term splits into 4T1g, 4T2g, 4A2g under octahedral field
# The energy levels are:
# 4T1g: 0
# 4T2g: Dq
# 4A2g: 2Dq
# Then excited terms (doublets): 2Eg, 2T1g, 2T2g, 2A1g
# 2Eg: 2Dq + 2B
# 2T1g: 3Dq + 2B
# 2T2g: 3Dq + 3B
# 2A1g: 4Dq + 2B

# But we must check for possible crossings and correct ordering
# For d7, the 2Eg term is often low, but we must compute for each Dq/B

# We'll compute E/B for each term
results = []

for dq_over_b in dq_over_b_values:
    Dq = dq_over_b * B
    
    # Compute energies in cm^-1
    # 4T1g (ground) = 0
    # 4T2g = Dq
    # 4A2g = 2*Dq
    # 2Eg = 2*Dq + 2*B
    # 2T1g = 3*Dq + 2*B
    # 2T2g = 3*Dq + 3*B
    # 2A1g = 4*Dq + 2*B
    
    terms = [
        ("4T2g", Dq),
        ("4A2g", 2*Dq),
        ("2Eg", 2*Dq + 2*B),
        ("2T1g", 3*Dq + 2*B),
        ("2T2g", 3*Dq + 3*B),
        ("2A1g", 4*Dq + 2*B)
    ]
    
    # Convert to E/B
    terms_eb = [(term, energy / B) for term, energy in terms]
    
    # Sort by energy (E/B)
    terms_eb.sort(key=lambda x: x[1])
    
    # Take the three lowest excited terms
    top_three = terms_eb[:3]
    
    # Append to results
    for term, e_over_b in top_three:
        results.append({
            "dq_over_b": dq_over_b,
            "term": term,
            "e_over_b": e_over_b
        })

# Output results
import json
print(json.dumps(results, indent=2))
EOF