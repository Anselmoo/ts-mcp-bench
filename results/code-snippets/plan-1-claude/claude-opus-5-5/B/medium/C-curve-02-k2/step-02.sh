
cd ~ 2>/dev/null || cd $(mktemp -d); echo $PWD; touch x && echo ok
