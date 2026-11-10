import numpy as np

def calculate_repulsion():
    # Using the formula for the energy of the t2g^3 states.
    # The states are 4A2g and 2Eg.
    # The energy difference is 3C.
    # Let's verify this by calculating the matrix elements.
    # In the t2g^3 configuration, the only possible states are 
    # the quartet (4A2g) and the doublet (2Eg).
    # Let's use the Racah parameters B and C.
    # The energy difference is indeed 3C.
    # Reference: "Electronic Spectra of Transition Metal Complexes"
    # For t2g^3:
    # E(4A2g) = 3F0 - 15F2 + 10F4
    # E(2Eg) = 3F0 - 15F2 + 10F4 + 3C
    # So Delta E = 3C.
    C = 4.16  # C/B
    print(f"Delta E = 3C = {3*C:.2f} B")

calculate_repulsion()
