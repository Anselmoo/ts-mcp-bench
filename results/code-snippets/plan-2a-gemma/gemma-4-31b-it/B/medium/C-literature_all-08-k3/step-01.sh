cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(p, nu1, nu2, nu3):
    Dq, B = p
    # Energy expressions for d5 high spin relative to 6A1g
    # Nu3 corresponds to 4A1g(G) and 4Eg(G), which is approx 10B
    # Nu2 corresponds to 4T2g(G)
    # Nu1 corresponds to 4T1g(G)
    
    # Using the approximations from standard tables:
    # E(4A1g, 4Eg) = 10 B
    # E(4T2g) = -10 Dq + 10 B + (some correction)
    # This is not quite right. Let's use the full secular determinant or known simplified forms.
    
    # From a standard source (e.g., "Ligand Field Theory" by Figgis):
    # E(4A1g, 4Eg) = 10 B
    # E(4T2g) = -10 Dq + 10 B + \sqrt{100 Dq^2 + 20 B^2 - 100 B Dq + 25 B^2} / 2 ... no.
    
    # Actually, for d5, the common expressions for the lowest 3 bands are:
    # nu3 = 10 B
    # nu2 = 10 B - 10 Dq + something
    # This is getting confusing. Let's use the known relation:
    # nu3 = 10 B
    # nu2 = 10 B - 10 Dq + sqrt(100 Dq^2 + 25 B^2) ? No.
    
    # Let's re-evaluate.
    # For Mn(II) high spin, the transitions are:
    # 1. 6A1 -> 4T1(G)
    # 2. 6A1 -> 4T2(G)
    # 3. 6A1 -> 4Eg(G) / 4A1g(G)
    
    # Energies from Tanabe-Sugano for d5:
    # nu_3 (4Eg, 4A1g) = 10 B
    # nu_2 (4T2g) = -10 Dq + 10 B + sqrt(100 Dq^2 + ... )
    
    # Let's look at the 4T1g(G) and 4T2g(G) expressions.
    # The states are 4T1g(G), 4T2g(G), 4A1g(G), 4E_g(G).
    # 4A1g and 4E_g are degenerate and at 10B.
    # 4T2g is at E = -10 Dq + 10 B + sqrt( (10 Dq - 10 B)^2 + 25 B^2 ) / 2 ? No.
    
    # Let's use the standard formula:
    # nu_3 = 10 B
    # nu_2 = 10 B - 10 Dq
    # nu_1 = 10 B - 10 Dq - (some shift)
    # That's too simple.
    
    # Let's use a better set of formulas for d5:
    # E(4Eg, 4A1g) = 10 B
    # E(4T2g) = 10 B - 10 Dq + \sqrt{100 Dq^2 + 25 B^2} / 2 ... no.
    
    # Correct formulas for d5 high spin:
    # v3 = 10 B
    # v2 = -10 Dq + 10 B + sqrt(100 Dq^2 + 25 B^2)
    # v1 = -10 Dq + 10 B - sqrt(100 Dq^2 + something)
    
    # Actually, a very common approximation for high spin d5:
    # v3 = 10 B
    # v2 = 10 B - 10 Dq (roughly)
    # v1 = 10 B - 20 Dq (roughly)
    # Let's check if 19180, 22130, 23370 fit this.
    # 10 B = 23370 => B = 2337.
    # 10 B - 10 Dq = 22130 => 10 Dq = 1240 => Dq = 124.
    # 10 B - 20 Dq = 23370 - 2480 = 20890. (nu1 is 19180).
    # Difference is 1710.
    
    # Let's try to be more precise.
    # The states 4T1(G) and 4T2(G) are from 4G.
    # 4G splits into 4T1, 4T2, 4A1, 4E.
    # For d5, the energies are:
    # E(4A1, 4E) = 10 B
    # E(4T2) = 10 B - 10 Dq + \sqrt{100 Dq^2 + 25 B^2} ? No.
    
    # Let's use the matrix for the 4G term in O_h.
    # The states are 4T1(G), 4T2(G), 4A1(G), 4E(G).
    # The energies can be solved from the secular determinant.
    # But wait, the prompt asks for B and C as well.
    # Transitions to 4T1g can be shifted by configuration interaction with 4T1g(P).
    # The 4T1g(G) and 4T1g(P) states mix.
    # E(4T1g) = 1/2 [ (E_G + E_P) +/- sqrt((E_G - E_P)^2 + 24 B^2) ]
    # E_G(4T1) = -10 Dq + 10 B ...?
    
    # Let's rethink. 
    # For Mn(II) octahedral complexes:
    # nu_3 (4Eg/4A1g) = 10 B
    # nu_2 (4T2g) = 10 B - 10 Dq
    # nu_1 (4T1g) = 10 B - 10 Dq - (interaction with 4T1g(P))
    
    # Actually, the transition to 4T1g is:
    # nu_1 = E(4T1g) - E(6A1g)
    # The 4T1g states come from 4G and 4P.
    # For the free ion, 4G is at 10 B, 4P is at 15 B + ...
    # Actually, the 4P state is at 15 B.
    # In O_h, 4P becomes 4T1g(P).
    # 4G becomes 4T1g(G), 4T2g(G), 4A1g(G), 4Eg(G).
    # E(4T2g(G)) = 10 B - 10 Dq
    # E(4A1g(G), 4Eg(G)) = 10 B
    # E(4T1g(G)) and E(4T1g(P)) are found from:
    # | (E_G - E)   3 B |
    # | 3 B        (E_P - E) | = 0
    # where E_G = 10 B - 20 Dq (roughly)
    # and E_P = 15 B (roughly)
    
    # Let's try this model:
    # nu3 = 10 B
    # nu2 = 10 B - 10 Dq
    # nu1 = solving the 2x2 for 4T1.
    
    # Let's test:
    # nu3 = 23370 => B = 2337
    # nu2 = 22130 => 10 Dq = 23370 - 22130 = 1240 => Dq = 124.
    # Then E_G(4T1) = 10 B - 20 Dq = 23370 - 2480 = 20890.
    # E_P(4T1) = 15 B + some Dq dependence?
    # 4P in O_h is 4T1g. Its energy is 15 B. (Relative to 6A1g).
    # Let's check the interaction:
    # E_G = 20890, E_P = 15 * 2337 = 35055.
    # Delta = E_P - E_G = 35055 - 20890 = 14165.
    # Interaction term is 3 B? No, for d5 it's 6 B. (Let me check).
    # The matrix element <4T1(G)|H|4T1(P)> = 6 B.
    # E = 1/2 [ (20890 + 35055) - sqrt(14165^2 + (2 * 6 * 2337)^2) ]
    # E = 1/2 [ 55945 - sqrt(14165^2 + 28044^2) ]
    # E = 1/2 [ 55945 - 31418 ] = 12263.
    # This is far from 19180.
    
    # Maybe my E_G and E_P are wrong.
    # Let's look for the correct expressions for d5 energies.
    # A better source:
    # nu_3 = 10 B
    # nu_2 = 10 B - 10 Dq + (correction)
    # Actually, let's use:
    # nu_1 = 4T1(G)
    # nu_2 = 4T2(G)
    # nu_3 = 4Eg, 4A1g
    # For d5:
    # E(4A1g, 4Eg) = 10 B
    # E(4T2g) = 10 B - 10 Dq
    # E(4T1g) is the lower root of x^2 - (E_G + E_P)x + E_G E_P - (6 B)^2 = 0
    # where E_G = 10 B - 20 Dq
    # and E_P = 15 B
    # Wait, maybe the bands are assigned differently?
    # "19180, 22130 and 23370 (assigned 4T1, 4T2, 4E, respectively)"
    # So nu1 = 4T1, nu2 = 4T2, nu3 = 4E.
    # My E(4T2) = 10 B - 10 Dq = 22130.
    # My E(4E) = 10 B = 23370.
    # This implies 10 Dq = 1240.
    # Then E_G(4T1) = 10 B - 20 Dq = 23370 - 2480 = 20890.
    # Now we need the root of x^2 - (20890 + 35055)x + (20890 * 35055 - (6 * 2337)^2) = 0.
    # x = 1/2 [ 55945 - sqrt(14165^2 + 28044^2) ] = 12263.
    # Still too low.
    
    # Is it possible that 4T1 is not 4T1(G)? 
    # No, the lowest band is always 4T1(G).
    # Maybe E_G(4T1) is not 10 B - 20 Dq?
    # Let's use the Tanabe-Sugano formula for d5.
    # E(4T2g) = 10 B - 10 Dq (approximately)
    # E(4T1g) = 10 B - 20 Dq (approximately)
    # But the interaction with 4T1g(P) pushes 4T1g(G) DOWN.
    # To get it to 19180, it should have been higher before interaction.
    # But 20890 is already higher than 19180.
    # 20890 -> 12263 is a huge drop.
    
    # Let's check if nu_1 is 4T2 and nu_2 is 4T1?
    # No, the prompt says "assigned 4T1, 4T2, 4E".
    
    # Let's reconsider the B and C values.
    # Usually, B for Mn(II) is around 800-1000 cm-1.
    # If B = 900, then 10 B = 9000.
    # But nu_3 = 23370. That's 10 B?
    # If 10 B = 23370, B = 2337. This is very high for Mn(II).
    # Free ion Mn(II) has B = 960 cm-1.
    # A value of 2337 is impossible.
    
    # Wait! The states for d5 are not 6A1 -> 4G.
    # The 4G state is not the only one.
    # Let's look at the Tanabe-Sugano diagram for d5 again.
    # The transitions are 6A1 -> 4T2, 4T1, 4Eg...
    # The energy of 4T2 is 10 Dq.
    # The energy of 4T1 is ...
    # Let's use the formula:
    # nu_1 (4T1) = -10 Dq + 10 B + ...
    # Actually, let's use the formula from a paper on Mn(II) complexes.
    # For high spin d5:
    # E(4T1) = -10 Dq + 10 B + ...
    # E(4T2) = 0 + 10 B + ...
    # E(4Eg) = 10 Dq + 10 B + ...
    # This doesn't seem right.
    
    # Let's try the formulas:
    # nu_1 = -10 Dq + 10 B
    # nu_2 = 0 Dq + 10 B
    # nu_3 = 10 Dq + 10 B
    # If nu_2 = 10 B = 22130, then B = 2213.
    # If nu_3 = 10 Dq + 22130 = 23370, then 10 Dq = 1240, Dq = 124.
    # If nu_1 = -10 Dq + 10 B = -1240 + 22130 = 20890.
    # Still not 19180.
    
    # Let's look at the actual values for MnCl2.
    # MnCl2 is often [MnCl4]2- or MnCl2 * 6H2O.
    # For [Mn(H2O)6]2+, the bands are around 18000, 22000, 25000.
    # Typical values: Dq = 800-900 cm-1, B = 800-900 cm-1.
    # If Dq = 900 and B = 900:
    # 10 Dq = 9000.
    # Let's use the Tanabe-Sugano energy expressions for d5.
    # Energy of 4T1(G) = -10 Dq + ( some function of B and Dq )
    # Energy of 4T2(G) = 0 Dq + ( some function of B and Dq )
    # Energy of 4Eg(G) = 10 Dq + ( some function of B and Dq )
    # The function is approximately 10 B.
    # nu_1 = -10 Dq + 10 B
    # nu_2 = 0 Dq + 10 B
    # nu_3 = 10 Dq + 10 B
    # This is what I just tried.
    
    # Let's try to use the 4T1 mixing.
    # E(4T2) = 10 B - 10 Dq ? No.
    # E(4T2) = 10 B + 0 Dq ? No.
    
    # Let's use the most reliable formulas for d5 high spin:
    # nu_1 = E(4T1) - E(6A1)
    # nu_2 = E(4T2) - E(6A1)
    # nu_3 = E(4Eg) - E(6A1)
    # nu_3 = 10 B
    # nu_2 = 10 B - 10 Dq + \sqrt{100 Dq^2 + 25 B^2} / 2 ? No.
    
    # Let's search for "MnCl2 d5 ligand field parameters".
    # Actually, let's use the tools to find the energy expressions.
EOF
python3 solver.py
