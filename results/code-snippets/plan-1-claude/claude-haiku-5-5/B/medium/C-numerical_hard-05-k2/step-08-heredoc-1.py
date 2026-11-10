import re
src=open('d6.py').read()
old="""                if c==d or not (s>>d)&1: continue
                s1=s^(1<<d); g1=(-1)**bin(s&((1<<d)-1)).count('1')
                if not (s1>>c)&1: continue
                s2=s1^(1<<c); g2=(-1)**bin(s1&((1<<c)-1)).count('1')"""
new="""                if c==d or not (s>>c)&1: continue
                s1=s^(1<<c); g1=(-1)**bin(s&((1<<c)-1)).count('1')
                if not (s1>>d)&1: continue
                s2=s1^(1<<d); g2=(-1)**bin(s1&((1<<d)-1)).count('1')"""
assert old in src
open('d6.py','w').write(src.replace(old,new))
