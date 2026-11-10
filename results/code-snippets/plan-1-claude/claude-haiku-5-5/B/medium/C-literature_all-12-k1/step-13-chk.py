import numpy as np
from fit2 import spectra
for C in (0,2000,4000):
    q,d=spectra(615,800,C); print(C, np.round(q-q[0],1))
