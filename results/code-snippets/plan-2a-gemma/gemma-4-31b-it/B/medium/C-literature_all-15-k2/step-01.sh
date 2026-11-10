cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def calculate_energies(B, Dq):
    Delta_o = 10 * Dq
    # For d7 high spin (equivalent to d3 holes in an inverted field, or using the TS matrix)
    # The states are 4T1(F), 4T2(F), 4A2(F), 4T1(P)
    
    # Using the expressions for d3 but adapting to d7:
    # In d3: 4A2g is ground, 4T2g is Delta_o, 4T1g(F) and 4T1g(P) are mixed.
    # In d7: 4T1g(F) is ground, 4T2g is Delta_o + E(4T1g(F)), 4A2g is 2*Delta_o + E(4T1g(F))
    # Actually, the energy levels of d7 high spin are simply those of d3 high spin 
    # mirrored and shifted.
    # Let's use the energy expressions for d3 high spin:
    # E(4A2g) = 0
    # E(4T2g) = Delta_o
    # E(4T1g) are roots of x^2 - (15B + 4*Delta_o)x + (15B*Delta_o - 12*B^2) = 0? No.
    
    # Correct matrix for 4T1g states in d3:
    # [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 4*Delta_o + 15*B ]] ? No.
    
    # Let's use a simpler approach for d7:
    # nu1 = E(4T2) - E(4T1(F))
    # nu2 = E(4A2) - E(4T1(F))
    # nu3 = E(4T1(P)) - E(4T1(F))
    # We know nu2 - nu1 = Delta_o
    # And E(4T1(F)) and E(4T1(P)) are the roots of:
    # E^2 - (15B + 4*Delta_o)E + (15B*Delta_o - 12*B^2) = 0 relative to some origin.
    
    # Actually, the transition energies for d7 (high spin) are:
    # nu1 = 10Dq - 4B (approx)
    # nu2 = 20Dq - 4B (approx)
    # nu3 = 15B + 10Dq - 4B = 11B + 10Dq (approx)
    
    # More exact expressions from a source for d7:
    # E(4T1g(F)) = -15B + 4*Delta_o + 0.5 * np.sqrt((15*B - 4*Delta_o)**2 + 12*Delta_o**2)
    # E(4T2g) = -15B + 4*Delta_o - 0.5 * np.sqrt((15*B - 4*Delta_o)**2 + 12*Delta_o**2) + Delta_o
    # E(4A2g) = -15B + 6*Delta_o
    # E(4T1g(P)) = -15B + 4*Delta_o + 0.5 * np.sqrt((15*B - 4*Delta_o)**2 + 12*Delta_o**2) + 30*B ? No.
    
    # Let's use the property that E(4T1(P)) - E(4T1(F)) = nu3
    # In d3, E(4T1(P)) - E(4T1(F)) = nu3 - nu2
    # In d7, nu3 is the transition to 4T1(P).
    # Let's use the 4T1 matrix:
    # H = [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 4*Delta_o + 15*B ]] ? No.
    
    # Let's use the relation from a table:
    # nu1 = 8.5 B + 10 Dq - sqrt(...)
    # Actually, there's a simpler way.
    # nu1 = 8480, nu2 = 16305, nu3 = 20360
    # Delta_o = nu2 - nu1 = 7825
    # Then nu1 = 8480.
    # For d7: nu1 = Delta_o - (some function of B, Delta_o)
    # Let's use the 4T1 energies:
    # E1, E2 = eigenvalues of [[ -15*B + 4*Delta_o, 6*B ], [ 6*B, 15*B + 4*Delta_o ]]
    # This is for d3. For d7, the ground state is the lower one.
    # Wait, let's just use the formula for nu3 for d3 and adapt it.
    # nu3(d3) = E(4T1(P)) - E(4A2g)
    # nu2(d3) = E(4T1(F)) - E(4A2g)
    # nu3(d7) = E(4T1(P)) - E(4T1(F)) = nu3(d3) - nu2(d3)
    
    # Let's calculate nu3(d3) - nu2(d3) for a given B, Delta_o:
    # E(4T1g) are roots of (E - 4*Delta_o)^2 - (15*B)^2 - (6*B)^2 = 0 ? No.
    # The matrix for 4T1g in d3 is:
    # [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 4*Delta_o + 15*B ]]
    # Eigenvalues: 4*Delta_o +/- sqrt((15*B)^2 + (6*B)^2) = 4*Delta_o +/- sqrt(225+36)*B = 4*Delta_o +/- sqrt(261)*B
    # So nu3(d3) = 4*Delta_o + 16.155*B
    # nu2(d3) = 4*Delta_o - 16.155*B
    # Then nu3(d7) = nu3(d3) - nu2(d3) = 32.31*B
    # But this is for the case where Delta_o is small? No, this is the exact result for this matrix.
    # Let's check if this matrix is correct.
    # For d3, the transitions are 4A2 -> 4T2, 4A2 -> 4T1(F), 4A2 -> 4T1(P).
    # nu1 = Delta_o
    # nu2 = 4*Delta_o - 16.155*B
    # nu3 = 4*Delta_o + 16.155*B
    # This doesn't look right. 4*Delta_o is too large.
    
    # Let's use the known result:
    # For d3, nu2 = 4*Delta_o - 15B + ...
    # Let's try a different matrix.
    # E(4T1g) = 4*Delta_o + ( -15*B +/- sqrt( (15*B)^2 + 12*B^2 ) ) ? No.
    
    # Let's use the formula:
    # nu3(d7) = E(4T1(P)) - E(4T1(F))
    # From a reliable table, for d7:
    # nu1 = 10Dq - 4B
    # nu2 = 20Dq - 4B
    # nu3 = 15B + 10Dq - 4B = 11B + 10Dq
    # Let's see if this fits:
    # 16305 - 8480 = 7825 = 10Dq. Correct.
    # 8480 = 7825 - 4B => 4B = -655 (B is negative, impossible)
    # So the approx is too simple.
    
    # Let's use the actual Tanabe-Sugano matrix for 4T1g:
    # H = [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 4*Delta_o + 15*B ]] is not right.
    # The correct matrix for 4T1g in d3 is:
    # [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 15*B ]] ? No.
    # Let's use the one from a textbook:
    # E1 = 4*Delta_o - 15*B + sqrt( (15*B - 4*Delta_o)^2 + 12*B^2 ) / 2 ? No.
    
    # Let's try this:
    # Delta_o = 7825
    # nu1 = 8480
    # nu3 = 20360
    # In d7, nu1 = E(4T2) - E(4T1(F))
    # E(4T2) = Delta_o + E(4T1(F)) is only if B=0.
    # With B, E(4T2) - E(4T1(F)) = Delta_o + (E(4T1(F))_B - E(4T1(F))_0) ...
    # Let's use the formula for nu1 and nu3 for d7.
    # nu1 = 10Dq + 8B - sqrt(256B^2 + 100BDq - 160Dq^2) ? No.
    
    # Let's use the Python tool to find B by iterating over B and using the 4T1 matrix.
    # I'll use the matrix:
    # [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 15*B ]] - no.
    # Let's try: [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 4*Delta_o + 15*B ]] was for d3.
    # Let's try this one: E(4T1(F)) = 4*Delta_o - 15*B, E(4T1(P)) = 15*B.
    # Then nu3 = E(4T1(P)) - E(4T1(F)) = 30*B - 4*Delta_o.
    # 20360 = 30*B - 4*7825 = 30*B - 31300 => 30*B = 51660 => B = 1722.
    # Now let's check nu1:
    # For d7, E(4T2) = Delta_o + E(4T1(F))?
    # If E(4T1(F)) = 4*Delta_o - 15*B, then E(4T2) = 5*Delta_o - 15*B.
    # nu1 = E(4T2) - E(4T1(F)) = Delta_o = 7825.
    # But nu1 = 8480. So it's close.
    
    return None

# Let's try the 4T1g matrix again.
# For d3:
# H = [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 15*B ]] - No.
# Let's use:
# E(4T1(F)) = 4*Delta_o - 15*B
# E(4T1(P)) = 15*B
# Then they mix.
# E = 0.5 * (4*Delta_o - 15*B + 15*B) +/- 0.5 * sqrt( (4*Delta_o - 30*B)^2 + 4*(6*B)^2 )
# E = 2*Delta_o +/- 0.5 * sqrt( 16*Delta_o^2 - 240*Delta_o*B + 900*B^2 + 144*B^2 )
# E = 2*Delta_o +/- 0.5 * sqrt( 16*Delta_o^2 - 240*Delta_o*B + 1044*B^2 )
# For d7, the ground state is the lower one: E(4T1(F)) = 2*Delta_o - 0.5 * sqrt(...)
# E(4T1(P)) = 2*Delta_o + 0.5 * sqrt(...)
# nu3 = E(4T1(P)) - E(4T1(F)) = sqrt( 16*Delta_o^2 - 240*Delta_o*B + 1044*B^2 )
# Also E(4T2) = Delta_o + E(4T1(F)) ? No.
# For d7, E(4T2) = Delta_o + E(4T1(F)) is exactly true if the interaction is the same?
# Let's check nu1: nu1 = E(4T2) - E(4T1(F)) = Delta_o.
# But nu1 = 8480 and Delta_o = 7825.
# This means E(4T2) - E(4T1(F)) = 8480, while Delta_o = 7825.
# Let's use the more accurate E(4T2) = Delta_o + E(4T1(F)) - (something).
# Actually, E(4T2) = Delta_o + E(4T1(F)) is a very good approximation.
# The difference is 8480 - 7825 = 655.
# Let's use nu3 to find B:
# 20360 = sqrt( 16*7825^2 - 240*7825*B + 1044*B^2 )
# 20360^2 = 16*7825^2 - 1878000*B + 1044*B^2
# 414529600 = 980410000 - 1878000*B + 1044*B^2
# 1044*B^2 - 1878000*B + 565880400 = 0
# B = [ 1878000 +/- sqrt( 1878000^2 - 4*1044*565880400 ) ] / (2 * 1044)
# B = [ 1878000 +/- sqrt( 3.52688*10^12 - 2.3631*10^12 ) ] / 2088
# B = [ 1878000 +/- sqrt( 1.16378*10^12 ) ] / 2088
# B = [ 1878000 +/- 1078786 ] / 2088
# B1 = 2956786 / 2088 = 1416
# B2 = 799214 / 2088 = 382
# Typical B for Co2+ is 800-1000. So 1416 or 382?
# Let's check B = 600-900.
# If B = 800, nu3 = sqrt( 16*7825^2 - 240*7825*800 + 1044*800^2 )
# nu3 = sqrt( 980.4*10^6 - 1502.4*10^6 + 668.2*10^6 ) = sqrt( 146.2*10^6 ) = 12091.
# Too small. We need nu3 = 20360.
# So we need B larger. Let's try B = 1416.
# nu3 = sqrt( 980.4*10^6 - 240*7825*1416 + 1044*1416^2 )
# nu3 = sqrt( 980.4*10^6 - 2660.5*10^6 + 2092.5*10^6 ) = sqrt( 412.4*10^6 ) = 20307.
# This is very close to 20360!
# So B is approx 1416.
# But B for Co2+ is usually around 900. 1416 is high, but possible for some ligands.
# Let's check the 4A2 state.
# nu2 = E(4A2) - E(4T1(F))
# In d7, E(4A2) = 2*Delta_o + E(4T1(F))? No.
# For d7, E(4A2) - E(4T2) = Delta_o.
# So nu2 - nu1 = Delta_o.
# 16305 - 8480 = 7825. This matches Delta_o.
# So B = 1416, Delta_o = 7825.
# Let's check the spin-forbidden transition nu4 = 21001.
# nu4 = E(2T1) - E(4T1).
# The 2T1 state in d7 is often around 20000-25000.
# 21001 is consistent.
# What about C?
# For d7, E(2T1) = nu4 + E(4T1(F)).
# The energy of the 2T1 state depends on B and C.
# E(2T1) = 15B + 10Dq - 4B ? No.
# For Co2+, E(2T1) is approx 15B + 10Dq?
# Let's use the formula E(2T1) = 15B + 10Dq - 4B = 11B + 10Dq.
# 21001 = 11*1416 + 7825 = 15576 + 7825 = 23401.
# A bit high, but close.
# To find C, we need a more accurate formula for E(2T1).
# E(2T1) = 15B + 10Dq - 2B + ... No.
# Actually, the 2T1 state is usually expressed as a function of B and C.
# E(2T1) = 15B + 10Dq - 4B + (some function of C).
# For d7, E(2T1) = 15B + 10Dq - 2B ?
# Let's use the formula E(2T1) = 15B + 10Dq - (some constant) * B.
# Most sources say E(2T1) = 15B + 10Dq for d3/d7.
# Let's use 21001 = 15B + 10Dq - 11B ? No.
# For d7, E(2T1) - E(4T1(F)) = nu4.
# nu4 = 21001.
# 15B + 10Dq - E(4T1(F)) = 21001.
# E(4T1(F)) = 2*Delta_o - 0.5 * sqrt( 16*Delta_o^2 - 240*Delta_o*B + 1044*B^2 )
# E(4T1(F)) = 2*7825 - 0.5 * 20360 = 15650 - 10180 = 5470.
# Then nu4 = 15B + 10Dq - 5470 = 15*1416 + 7825 - 5470 = 21240 + 7825 - 5470 = 23595.
# Still a bit high.
# Maybe B is smaller?
# If B = 1200:
# nu3 = sqrt( 16*7825^2 - 240*7825*1200 + 1044*1200^2 ) = sqrt( 980.4*10^6 - 2253.6*10^6 + 1503.3*10^6 ) = sqrt( 230.1*10^6 ) = 15169.
# Too small.
# So B must be around 1400.
# Let's check C. The relation between B and C for transition metals is often C = 4B.
# Let's see if we can find C from the 2T1 state.
# E(2T1) = 15B + 10Dq - 3C ? No.
# For d7, E(2T1) = 15B + 10Dq - 2B + ...
# Let's use a standard value for C if not enough info, but the question asks for C.
# Wait, the 2T1 state is 2T1(2)?
# The states for d7 are 4T1(F), 4T2, 4A2, 4T1(P) and 2T1, 2T2, 2A1.
# 2T1(2) is the second 2T1 state?
# No, usually it's just 2T1.
# Let's re-read: "2T1(2)".
# This might mean it's the second state of that symmetry.
# For d7, there are multiple 2T1 states.
# The lowest 2T1 is 2T1(F).
# E(2T1(F)) = -3B + 10Dq + ... No.
# Let's use the formula for the 2T1(F) state:
# E(2T1(F)) = -B + 10Dq ? No.
# For d7, E(2T1(F)) = 15B + 10Dq - 4B - 3C? No.
# Let's use the common formula for the 2T1 transition in Co2+:
# nu4 = 15B + 10Dq - 4B - C? No.
# Let's try: nu4 = 15B + 10Dq - 3B - 4C?
# Actually, a very common formula is nu(2T1) = 10Dq + 15B - 3B - 4C = 10Dq + 12B - 4C.
# 21001 = 7825 + 12*1416 - 4C = 7825 + 16992 - 4C = 24817 - 4C
# 4C = 24817 - 21001 = 3816 => C = 954.
# This gives C < B, which is unusual (usually C approx 4B).
# Let's re-calculate B more carefully.
# nu3 = 20360, Delta_o = 7825.
# 20360^2 = 16*7825^2 - 240*7825*B + 1044*B^2
# 414529600 = 980410000 - 1878000*B + 1044*B^2
# 1044*B^2 - 1878000*B + 565880400 = 0
# B = 1416 (as before).
# Let's check the nu1 = 8480.
# nu1 = E(4T2) - E(4T1(F)) = Delta_o + (E(4T1(F)) - E(4T1(F))) = Delta_o.
# But it's 8480. The difference is 8480 - 7825 = 655.
# This difference comes from the mixing of 4T1(F) and 4T1(P).
# E(4T1(F)) = 2*Delta_o - 0.5 * nu3 = 15650 - 10180 = 5470.
# E(4T2) = E(4T1(F)) + Delta_o = 5470 + 7825 = 13295.
# Then nu1 = 13295 - 5470 = 7825.
# To get nu1 = 8480, we need E(4T2) to be higher.
# E(4T2) = -15B + 5*Delta_o - 0.5 * sqrt((15B-4*Delta_o)^2 + 12*Delta_o^2) + (something)?
# Let's use a Python script to find the best B, Dq.
EOF
python3 solver.py
