Changes in this version (260824_1):
    Fixed a bug in command formatting when sending via TCP socket (added \n)
    Rewrote a few pieces of code to use the TCP socket and not the system method of sending commands.
    Added SetCW() to create a basis operating profile for CW.  
    Minor tweeks to Scott()
    Created a Test unction, a placeholder for: "pip install -e ." using the .toml file