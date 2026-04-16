#!/usr/bin/env python3
import re

# The pattern needs to match literal $ followed by [ ... ]
# In Python regex:
#   \$ matches literal $ (dollar is only special as an anchor at end of pattern)
#   \[ matches literal [

# Test approach 1: escape dollar with \$
p1 = re.compile(r"\$\[[^\]]*\]")
print("Pattern 1:", repr(p1.pattern))
print("  $[foo]:", p1.match("$[foo]"))
print("  $[5+3]:", p1.match("$[5+3]"))

# Test approach 2: simpler with .*? instead of [^\]]*
p2 = re.compile(r"\$\[.*?\]")
print("\nPattern 2:", repr(p2.pattern))
print("  $[foo]:", p2.match("$[foo]"))
print("  $[5+3]:", p2.match("$[5+3]"))

# Test approach 3: check if $ needs escaping
p3 = re.compile(r"\$\[\]")
print("\nPattern 3 (exact $[]]):", repr(p3.pattern))
print("  $[]:", p3.match("$[]"))

# Test approach 4: what does $\[ actually match?
p4 = re.compile(r"\$\[")
print("\nPattern 4 ($[):", repr(p4.pattern))
print("  $[:", p4.match("$["))
print("  $[foo]:", p4.match("$[foo]"))
