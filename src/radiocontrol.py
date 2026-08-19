# import time
import socket
import os

global DEBUG 
_socket_handle = None

DEBUG = True

CW_Mode = "MD03"
USB_Mode = "MD02"
LSB_Mode = "MD01"
AM_Mode = "MD04"

CW_Setting = "02"

Mode_CW = "01"
Sel_Treble = "01"
Sel_Mid = "02"
Sel_Bass = "03"

Keyer_Setting = "02"
Keyer_type = "01"
Keyer_type_IambicB = "3"  # 0 = OFF, 1 = Bug, 2 = Iambic A, 3 = Iambic B, 4 = Ultimatic, 5 = ACS
Keyer_type_Off = "0"      # 0 = OFF, 1 = Bug, 2 = Iambic A, 3 = Iambic B, 4 = Ultimatic, 5 = ACS



Treble_Setting = "00"
Mid_Setting    = "00"
Bass_Setting   = "00"
CW_Audio_Treble = "EX"+CW_Setting+Mode_CW+Sel_Treble+Treble_Setting
CW_Audio_Mid    = "EX"+CW_Setting+Mode_CW+Sel_Mid+Mid_Setting
CW_Audio_Bass   = "EX"+CW_Setting+Mode_CW+Sel_Bass+Bass_Setting





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

    print("\nSetting MONITOR to 25")
    # send_rig("W ML1025; 0")
    os.system('cmd /c "rigctl -m 2 --skip-init W ML1025; 0"')

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
    """ 
        02 = CW Setting
        01 = Mode CW
        16 = PC Keying
        0  = PC Keying Control off
    """
    send_rig(cmd)
    return

def pcon():
    if DEBUG:
        print("\npcon detected\n")
    cmd = "W EX0201162; 0"
    """ 
        02 = CW Setting
        01 = Mode CW
        16 = PC Keying
        2  = RTS
    """
    send_rig(cmd)
    return
 
def setCW():
    
#    CW_List = []"MD1",
    if DEBUG:
        print("\nSet radio for CW operation\n")
    cmd = "W MD1; 0"
    send_rig(cmd)
    return

# FT8 Settings
# set DATA-U mode
# Roofing filter to 3KHz
# AGC OFF
# Shift to 700Hz
# Width to 3KHz
# No filtering modes (DNR, DNF, NR, NB) etc.
# inside MODE PSK/DATA 
#   RPTT SELECT to RTS  (DAK-Y?)
#   RPORT GAIN to 6 
#   REAR SELECT to USB
#   DATA MOD SOURCE to REAR
#   DATA OUT LEVEL to 10
#   HCUT FREQ, LCUT FREQ to OFF
#   DATA SHIFT (SSB) was 1500, set to 0
#   