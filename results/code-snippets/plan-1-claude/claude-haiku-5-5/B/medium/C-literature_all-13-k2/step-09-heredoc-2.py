import sys; sys.path.insert(0,'/tmp')
import numpy as np
exec(open('/tmp/ls_core.py').read())
eq,ed=spectra(715,1000,4000)
print("quartets:", [(round(v-eq.min(),1),n) for v,n in uniq(eq)])
