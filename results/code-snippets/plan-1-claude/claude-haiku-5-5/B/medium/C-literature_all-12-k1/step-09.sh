python3 -c "
import ts,numpy as np
print(ts.h[0,0], ts.h[1,1], ts.h[2,2], ts.h[3,3])
print(ts.apply_ops([('c',0),('a',0)],(0,1)))
print(ts.apply_ops([('c',1),('a',1)],(0,1)))
"