# No specific search tool, but I can simulate a search by recalling knowledge or using Python if needed.
# Actually, let me check common textbooks or database values for [Cr(H2O)6]2+.
# Transition: 14260 cm-1 (max), 10970 cm-1 (shoulder).
# This specific example appears in some inorganic chemistry textbooks (e.g., Shriver & Atkins, Housecroft).
# In many cases, for high-spin d4, 10 Dq is estimated as the average or the peak position.
# However, the question specifically asks for B.
# Let's check if there is a transition to a triplet state.
# The ^3T1g state energy in d4:
# E(^3T1g) = -15 B + 10 Dq + (some term in Dq/B)
# No, the formula is more complex.
# Let's try to find the specific value of B for [Cr(H2O)6]2+.
# Common B for Cr(II) is around 800-900 cm-1.
# Let's see if 10970 cm-1 could be a triplet transition.
# If 14260 is 10 Dq, then B can be found from the other band.
# But 10970 is lower than 14260.
# For d4, the spin-allowed transition is the lowest energy transition in the O_h case.
# If there is a band at 10970, it must be part of the split 10 Dq band (JT distortion).
# If both bands are part of the split quintet transition, we still can't find B.
# Let me think if there is any other interpretation.
# Maybe the complex is NOT high-spin? "octahedral high-spin Cr(II)" - it is specified.
# Maybe the shoulder is a transition to a triplet state?
# But spin-forbidden transitions are usually higher in energy than the first spin-allowed for d4?
# For d4: ^5E_g (ground) -> ^5T_{2g} (spin allowed, 10 Dq)
# The triplet states ^3T_{1g}, ^3T_{2g}, etc., are generally higher in energy than ^5T_{2g} for small Dq/B.
# Wait, let's check the TS diagram for d4.
# At low Dq/B, ^5E_g is ground, ^5T_{2g} is at 10 Dq.
# The triplet states are indeed higher.
# So a band at 10,970 cm-1 cannot be a triplet if the main band is at 14,260 cm-1, unless 14,260 is not 10 Dq.
# But if 10,970 is 10 Dq, then 14,260 could be a triplet?
# Let's check: if 10 Dq = 10,970, is there a triplet at 14,260?
# E(^3T1g) = ...
# Actually, let's use the python tool to calculate the energies of d4 states for some B and Dq.
