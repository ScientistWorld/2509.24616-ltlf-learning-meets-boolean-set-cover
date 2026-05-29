# Overview

`LTLf Learning Meets Boolean Set Cover` introduces Bolt, an LTLf learner that avoids exhaustive growth of temporal formulas by switching from bounded LTLf enumeration to Boolean Set Cover over already discovered formulas.

This workspace reproduces the core claim at small CPU scale: the Boolean Set Cover stage solves selected tasks that raw bounded VFB cannot solve at the same LTL size bound, while all learned formulas are independently validated.
