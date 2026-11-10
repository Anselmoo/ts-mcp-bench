import sys
sys.argv = ['x', '2']
exec(open('ts.py').read())
lv = analyze(0.0)
for e, S, nm in lv: print(round(e, 5), S, nm)
