
cd $TMPDIR && sed -i "s/\[('a',dd),('a',cc),('c',b),('c',a)\]/[('a',cc),('a',dd),('c',b),('c',a)]/" d3.py && python3 d3.py
