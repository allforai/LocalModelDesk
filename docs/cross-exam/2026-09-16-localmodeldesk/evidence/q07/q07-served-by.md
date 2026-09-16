=== lsof -i :8783 ===
COMMAND   PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
Python  48328   aa    4u  IPv4 0x796c3bcad66f9a6c      0t0  TCP localhost:8783 (LISTEN)

=== ps for pid 48328 ===
  PID  PPID COMMAND
48328     1 /opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python -m desk

=== env check for MOCK/USE_MOCK/STUB in server process ===
none found

=== grep repo for json-server/miragejs/nock/msw ===
no such deps in package.json (or no package.json)
