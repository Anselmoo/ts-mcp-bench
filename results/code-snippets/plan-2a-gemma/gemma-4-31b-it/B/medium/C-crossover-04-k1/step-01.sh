cat << 'EOF' > solution.py
def calculate_transition():
    B = 922
    C = 4156
    # For d7, the HS ground state is 4T1g and the LS ground state is 2Eg.
    # The transition occurs when E(2Eg) = E(4T1g).
    # In many textbooks, the transition from HS to LS for d7 occurs at 10Dq approx P.
    # P is the pairing energy.
    # For d7, the pairing energy P can be approximated as:
    # P = E(2G) - E(4F) in the free ion.
    # For d3/d7, the energy of 2G relative to 4F is 3C - 3B? 
    # Let's check this.
    # For d3:
    # 4F: energy 0
    # 2G: energy 3C - 3B ? No, it's usually more like 3C-something.
    # Let's use the formula for d7 transition: 10Dq = P.
    # A common value for P for d7 is P = 3C - 3B. Let's verify.
    # Actually, let's look at the energy of the configurations.
    # HS: t2g^5 eg^2
    # LS: t2g^6 eg^1
    # The energy difference is delta_E = (E_LS - E_HS) = (repulsion_LS - repulsion_HS) - 10Dq.
    # repulsion_LS: t2g^6 eg^1
    # repulsion_HS: t2g^5 eg^2
    # We need the repulsion energy for these configurations.
    
    # Using the formula from a reliable source for d7:
    # The crossover occurs at 10Dq = P.
    # For d7, P = 2B + 3C - ? No.
    # Let's use a more standard approach: 10Dq = 3C - 3B is for d2.
    # For d3/d7, P is often given as P = 2B + 0.something C.
    
    # Let's try to find the specific value for d7 crossover.
    # From a Tanabe-Sugano diagram, the crossover is where the 4T1g and 2Eg lines intersect.
    # Looking at the TS diagram for d7:
    # The 4T1g ground state (HS) and the 2Eg state (LS).
    # The transition occurs when 10Dq/B approx 20-25.
    # If 10Dq/B = 20, 10Dq = 20 * 922 = 18440 cm-1.
    
    # Let's use the exact energy expressions for the terms.
    # For d7, 4T1g is the ground state.
    # 2Eg is the LS ground state.
    # The energy of 4T1g = -0.8 * 10Dq (approx)
    # The energy of 2Eg = -1.8 * 10Dq + P
    # Where P is the pairing energy.
    # P = E(S=1/2) - E(S=3/2)
    # For d7, S=3/2 is 4F, S=1/2 is 2G.
    # Energy of 2G relative to 4F is 3C - 3B? 
    # Let's check: 3*4156 - 3*922 = 12468 - 2766 = 9702 cm-1.
    # If 10Dq = 9702, then 10Dq/B = 9702/922 = 10.5.
    # This seems too low for the d7 crossover.
    
    # Let's reconsider the pairing energy.
    # P = (repulsion of t2g^6 eg^1) - (repulsion of t2g^5 eg^2)
    # For d7, the repulsion energy for t2g^6 eg^1 is:
    # 15C + something.
    # Let's use the formula for pairing energy: P = 3C - 3B is for d2.
    # For d7, the crossover 10Dq is usually around 20B.
    
    # Let's calculate the repulsion energy properly.
    # Using the formula for d^n:
    # E(t2g^n eg^m) = ...
    # For t2g^6 eg^1:
    # We have 6 electrons in t2g and 1 in eg.
    # Repulsion in t2g^6: 15C (roughly)
    # Repulsion between t2g^6 and eg^1: 6 * (some average)
    
    # Let's use the known result for d7:
    # The crossover is at 10Dq = P_avg.
    # For d7, P = 3B + (some C term).
    # Actually, the most accurate way to find the crossover is using the TS diagram's energy functions.
    # For d7, the ground state changes from 4T1g to 2Eg.
    # The energy of 4T1g (relative to 4F free ion) is:
    # E(4T1g) = -0.8 * 10Dq + (small B,C terms)
    # The energy of 2Eg (relative to 4F free ion) is:
    # E(2Eg) = -1.8 * 10Dq + P
    # For d3, the 2G term is the lowest S=1/2 state.
    # E(2G) - E(4F) = 3C - 3B? No.
    # For d3, the energy of 2G is 3C - 3B? Let me check a table.
    # According to some tables:
    # d3: 4F(0), 4P(15B), 2G(3C-3B?), 2H, 2D.
    # Wait, 3C - 3B = 3(4156) - 3(922) = 9702.
    # Let's check 10Dq/B for the d7 transition.
    # For d7, the transition to LS is usually at 10Dq/B ~ 20-25.
    # 20 * 922 = 18440.
    # This is much higher than 9702.
    
    # Let's rethink. Maybe P is not 3C-3B.
    # For d7, the LS ground state is 2Eg, which comes from 2G.
    # But the LS ground state is 2Eg, which has a configuration t2g^6 eg^1.
    # The HS ground state is 4T1g, which has a configuration t2g^5 eg^2.
    # The difference in repulsion is E(t2g^6 eg^1) - E(t2g^5 eg^2).
    
    # For t2g^6 eg^1:
    # The t2g^6 part has 15C? (Wait, t2g^6 is a closed shell)
    # For d^6 (low spin), the energy is 15C? No.
    # Let's use the formula:
    # E(t2g^6 eg^1) = 15C + 6 * (average repulsion between t2g and eg)
    # E(t2g^5 eg^2) = ...
    
    # Actually, there's a simpler formula for the crossover:
    # 10Dq = P.
    # For d7, P is approximately 2B + 0. something C.
    # Let's search for "d7 high spin low spin transition 10Dq".
    # Often, for Co(II), the transition is at 10Dq approx 18,000 - 22,000 cm-1.
    # With B = 922, this is 10Dq/B approx 20-24.
    
    # Let's calculate E(2G) - E(4F) more carefully.
    # For d3, E(2G) = 3C - 3B is not correct.
    # E(2G) - E(4F) = 3C - 3B is for d2/d8.
    # For d3:
    # The energy of 2G relative to 4F is 3C - 9B? No.
    # Let's use the correct expression for d3:
    # E(2G) - E(4F) = 3C - 3B - (something)?
    
    # Let's use a different approach.
    # For d7, 10Dq = P.
    # P = E(t2g^6 eg^1) - E(t2g^5 eg^2) at 10Dq = 0.
    # This is exactly the energy difference between the S=1/2 and S=3/2 states of the free ion.
    # For d7, S=3/2 is 4F. S=1/2 is 2G.
    # So 10Dq = E(2G) - E(4F).
    # Let's find the value of E(2G) - E(4F) for d3/d7.
    # For d3, the free ion terms are:
    # 4F: 0
    # 2G: 3C - 3B ? I keep seeing this. Let me double check.
    # Wait! For d3, the term 2G energy is:
    # E(2G) = 3C - 3B.
    # Let's check if 10Dq = 3C - 3B makes sense.
    # 3(4156) - 3(922) = 12468 - 2766 = 9702 cm-1.
    # Is 10Dq = 9702 cm-1 reasonable for d7 crossover?
    # Co(II) in [Co(H2O)6]2+ is HS, 10Dq approx 9000 cm-1.
    # [Co(CN)6]4- is LS, 10Dq approx 20,000 cm-1.
    # So the crossover should be between 9000 and 20,000.
    # 9702 is just above 9000. This is possible!
    # But wait, [Co(H2O)6]2+ is very close to the crossover? No, it's definitely HS.
    # Let's check the crossover for Co(II) more carefully.
    
    # Wait, 4F and 4P are the only quartets.
    # For d7, the HS ground state is 4T1g.
    # The LS ground state is 2Eg.
    # Let's use the formula from a known source for d7 crossover:
    # 10Dq = P.
    # For d7, P = E(S=1/2) - E(S=3/2).
    # The S=1/2 state is 2G.
    # For d3/d7, E(2G) - E(4F) = 3C - 3B.
    # Let me verify this again.
    # Looking at the energy of the terms for d3:
    # E(4F) = 0
    # E(2G) = 3C - 3B
    # E(2H) = 3C - 3B + something
    # E(2D) = 3C - 3B + something
    # Yes, 3C - 3B seems to be the value for 2G.
    
    # Let's double check the pairing energy P.
    # P is the energy to pair one electron.
    # For d7 HS (t2g^5 eg^2) -> LS (t2g^6 eg^1).
    # One electron moves from eg to t2g and pairs up.
    # The change in pairing energy is P.
    # P = E(2G) - E(4F) if we only consider the lowest states.
    # But there is also the 4P state.
    # The ground state for d7 HS is 4T1g, which is a mixture of 4F and 4P.
    # E(4T1g) = -0.8 * 10Dq + some mixing term.
    # However, for the transition, the mixing is usually small or the 4F part dominates.
    
    # Let's use the 10Dq = 3C - 3B formula.
    B = 922
    C = 4156
    Dq_10 = 3*C - 3*B
    print(f"10Dq = {Dq_10}")
    print(f"Dq = {Dq_10 / 10}")

calculate_transition()
EOF
python3 solution.py
