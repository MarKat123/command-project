# import time
import socket
import os
import subprocess

global DEBUG 
_socket_handle = None

DEBUG = True

def get_socket_handle(host: str = 'localhost', port: int = 4532):
    """
    Returns the socket handle, opening it if not already open.
    Singleton pattern - only one socket opened for life of program.
    """
    global _socket_handle
    
    # Test if socket is already open and valid
    if _socket_handle is not None:
        try:
            # Send a zero-byte message to test if socket is still alive
            _socket_handle.send(b'')
            return _socket_handle  # Socket is good, return it
        except (socket.error, OSError):
            # Socket is dead, fall through to reopen it
            _socket_handle = None
    
    # Open the socket
    try:
        _socket_handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket_handle.connect((host, port))
        if DEBUG:
            print(f"Socket opened to {host}:{port}")
        return _socket_handle
    except socket.error as e:
        print(f"Failed to open socket: {e}")
        _socket_handle = None
        return None

def close_socket():
    """Cleanly close the socket when done"""
    global _socket_handle
    if _socket_handle is not None:
        try:
            _socket_handle.close()
            print("Socket closed")
        except socket.error as e:
            print(f"Error closing socket: {e}")
        finally:
            _socket_handle = None

def send_rig(cmd: str):      
    s = get_socket_handle()
    if s is None:
        print("No socket available")
        return None

    try:
        # Create a socket connection
        s.sendall(cmd.encode('utf-8'))
        if DEBUG:
            print(f"Sent command: {cmd.strip()}")

        # Optional: Read the rigctld response (e.g., RPRT 0 for success)
        # response = s.recv(1024).decode('utf-8')
        # print(f"Response: {response.strip()}")
        # return response
        return
    
    except socket.error as e:
        print(f"Socket error sending command: {e}")
        # Force socket to reopen next time
        global _socket_handle
        _socket_handle = None
        return None

def p5():
    if DEBUG:
        print("\np5 detected\n")
    send_rig("W PC005; 0")
    return

def p20():
    if DEBUG:
        print("\np20 detected\n")
    send_rig("W PC020; 0")
    return

def p40():
    if DEBUG:
        print("\np40 detected\n")
    send_rig("W PC040; 0")
    return

def p60():
    if DEBUG:
        print("\np60 detected\n")
    send_rig("W PC060; 0")
    return

def p80():
    if DEBUG:
        print("\np80 detected\n")
    send_rig("W PC080; 0")
    return


def p100():
    if DEBUG:
        print("\np100 detected\n")
    send_rig("W PC100; 0")
    return

def Scott():
    if DEBUG:
        print("\nScott detected\n")

    print("\nSetting BREAKIN OFF")
    send_rig("W BI0; 0")

    print("\nSetting MONITOR to 50")
    # send_rig("W ML1050; 0")
    os.system('cmd /c "rigctl -m 2 --skip-init W ML1050; 0"')

    print("\nSetting SPEED to 20 WPM")
    # send_rig("W KS020; 0")
    os.system('cmd /c "rigctl -m 2 --skip-init W KS020; 0"')

    return
 
def NoScott():
    if DEBUG:
        print("\nNoScott detected\n")

    print("\nSetting BREAKIN ON")
    send_rig("W BI1; 0")

    print("\nSetting MONITOR to 15")
    # send_rig("W ML1015; 0")
    os.system('cmd /c "rigctl -m 2 --skip-init W ML1015; 0"')

    print("\nSetting SPEED to 26 WPM")
    # send_rig("W KS026; 0")
    os.system('cmd /c "rigctl -m 2 --skip-init W KS026; 0"')

    return

def pcoff():
    if DEBUG:
        print("\npcoff detected\n")
    cmd = "W EX0201160; 0"
    send_rig(cmd)
    return

def pcon():
    if DEBUG:
        print("\npcon detected\n")
    cmd = "W EX0201162; 0"
    send_rig(cmd)
    return
 
def CapeCod():
    if DEBUG:
        print("\nCapeCod detected\n")
    subprocess.run(['setx', 'LOCATION_VAR', 'Cape'], check=True)
    return

def Charlotte():
    if DEBUG:
        print("\nCharlotte detected\n")
    subprocess.run(['setx', 'LOCATION_VAR', 'Charlotte'], check=True)
    return
