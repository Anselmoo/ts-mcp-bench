import re
src=open('/tmp/tsbench-run-711ytt10/w/d7.py').read()
src=src.replace("W = None\n","")
# add grid weights for rotation use
src+="\nWG = W\n"
open('/tmp/tsbench-run-711ytt10/w/d7.py','w').write(src)
