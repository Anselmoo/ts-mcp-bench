
cd <SANDBOX_TMP>/tmp.dJiUhyh28T && sed -i "s/if kind=='h':/if isinstance(kind,str):/; s/parts\['h'\]=assemble('h')/parts['h']=assemble('h')/" pre.py && timeout 500 python3 fit4.py 2>&1 | tail -4
