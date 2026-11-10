import numpy as np

B = 2060
Dq = 1417
term = np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq)
nu2 = 0.5 * (45*B + 10*Dq - term)
nu3 = 0.5 * (45*B + 10*Dq + term)
print(f"B = {B}, nu2 = {nu2}, nu3 = {nu3}")
