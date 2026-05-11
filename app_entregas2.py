import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "entregas"))
os.chdir(os.path.join(os.path.dirname(__file__), "entregas"))

exec(open("entregas/app_entregas2.py", encoding="utf-8").read())
