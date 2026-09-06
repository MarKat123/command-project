import socket
import winreg
import ctypes

_socket_handle = None

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

"""
Following are the backbone commands for radio control
get_socket_handle() - returns the socket handle, opening it if not already open
close_socket() - cleanly close the socket when done
send_rig(cmd) - sends a command to the rig via TCP socket and returns the response
"""



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
        if checkdebug():
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
        full_cmd = f"{cmd}\n"   # lowercase w, newline terminator
        s.sendall(full_cmd.encode('utf-8'))
        if checkdebug():
            print(f"Sent command: {full_cmd.strip()}")

        # ALWAYS drain the response, even for set commands,
        # or leftover bytes will corrupt the next read on this socket
        response = s.recv(1024).decode('utf-8').strip()
        if checkdebug():
            print(f"Response: {response}")
        return response
 
    except socket.error as e:
        print(f"Socket error sending command: {e}")
        # Force socket to reopen next time
        global _socket_handle
        _socket_handle = None
        return None
"""
Basic commands for the radio
p5, p20, p40, p60, p80, p100 - set power levels 
Scott - set radio for Scott CW operation via Zoom   
NoScott - set radio for normal CW operation
SetCW - set radio for CW operation with specific settings 
pcoff - turn off PC keying control
pcon - turn on PC keying control

"""
def p5():
    if checkdebug():
        print("\np5 detected\n")
    send_rig("W PC005; 0")
    return

def p20():
    if checkdebug():
        print("\np20 detected\n")
    send_rig("W PC020; 0")
    return

def p40():
    if checkdebug():
        print("\np40 detected\n")
    send_rig("W PC040; 0")
    return

def p60():
    if checkdebug():
        print("\np60 detected\n")
    send_rig("W PC060; 0")
    return

def p80():
    if checkdebug():
        print("\np80 detected\n")
    send_rig("W PC080; 0")
    return


def p100():
    if checkdebug():
        print("\np100 detected\n")
    send_rig("W PC100; 0")
    return

def Scott():
    if checkdebug():
        print("\nScott detected\n")

    send_rig("W BI0; 0")        # Set BREAK-IN to OFF
    send_rig("W ML1025; 0")     # Set MONITOR to 25
    send_rig("W KS020; 0")      # Set KEY SPEED to 20 WPM
    send_rig("W KR1; 0")        # Set KEYER to ON

    return
 
def NoScott():
    if checkdebug():
        print("\nNoScott detected\n")

    send_rig("W BI1; 0")        # Set BREAK-IN to ON
    send_rig("W ML1010; 0")     # Set MONITOR to 10
    send_rig("W KR1; 0")        # Set KEYER to ON
    send_rig("W KS024; 0")      # Set KEY SPEED to 24 WPM
    return

def pcoff():
    if checkdebug():
        print("\npcoff detected\n")

    """ 
        02 = CW Setting
        01 = Mode CW
        16 = PC Keying
        0  = PC Keying Control off
    """
    send_rig("W EX0201160; 0")
    return

def pcon():
    if checkdebug():
        print("\npcon detected\n")

    """ 
        02 = CW Setting
        01 = Mode CW
        16 = PC Keying
        2  = RTS
    """
    send_rig("W EX0201162; 0")
    return
 
def setCW():
    
#    MODE = "MD03", MONITOR = 15, SPEED = 24 WPM, BREAKIN = ON, 
#    PC KEYING = RTS, PC KEYING CONTROL = ON, CW AUDIO TREBLE = 0, CW AUDIO MID = 0, CW AUDIO BASS = 0  
#    PITCH = 550, BK-DELAY = 200
#    
    if checkdebug():
        print("\nSet radio for CW operation\n")
    send_rig("W MD03; 0")       # Set MODE to CW
    send_rig("W ML1010; 0")     # Set MONITOR to 10
    send_rig("W KS024; 0")      # Set KEY SPEED to 24 WPM
    send_rig("W BI1; 0")        # Set BREAK-IN to ON
    send_rig("W KR1; 0")        # Set KEYER to ON
    send_rig("W KP25; 0")       # Set PITCH to 550
    send_rig("W RF04; 0")       # Set ROOFING FILTER to 500Hz
    send_rig("W SH0007; 0")     # Set FILTER_SIDTH to 350Hz

    if setCWfrequency() == None:    # Set frequency to CW portion of band
        print("Failed to set CW frequency")
        return None

    send_rig("W AB; 0")         # Set VCOB to VCOA value 
    return 1

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
def getfrequency():
    if checkdebug():
        print("\nGet frequency detected\n")

    frequencystring= send_rig("W FA; 12")      # Send command to read frequency
    if frequencystring is None:
        print("No response from rig — comm error")
        return None
    if checkdebug():
        print(f"Frequency received: {frequencystring}")
        print(f"Frequency integer: {int(''.join(filter(str.isdigit, frequencystring)))}")

    return int("".join(filter(str.isdigit, frequencystring)))

def setfrequency(frequency: int):
    if checkdebug():
        print(f"\nSet frequency cmd  W FA{str(frequency).zfill(9)}; 0\n")
    send_rig(f"W FA{str(frequency).zfill(9)}; 0")

    if checkdebug():
        # read VFOA frequency to verify it was set correctly
        frequencystring = send_rig("W FA; 12")
        if frequencystring is not None:
            print(f"Verified frequency: {frequencystring}")
    return

def test():
    if checkdebug():
        print("\nTest function detected\n")
#        junk = test2()  # unused for now, but will be useful for future debug and testing
#        print("\nTest2 returned: ", junk, "\n")
        return 43

def setCWfrequency():
    if checkdebug():
        print("\nSet CW frequency function detected\n")
        # Set frequency to CW portion of band, to be used with SetCW
    currentfrequency = getfrequency()
    if currentfrequency is None:
        print("Failed to retrieve frequency")
        return None
        
    if currentfrequency >=  350000  and currentfrequency <=  3600000: return 1
    if currentfrequency >=  7000000 and currentfrequency <=  7125000: return 1
    if currentfrequency >= 10100000 and currentfrequency <= 10150000: return 1
    if currentfrequency >= 14000000 and currentfrequency <= 14150000: return 1
    if currentfrequency >= 18068000 and currentfrequency <= 18110000: return 1
    if currentfrequency >= 21000000 and currentfrequency <= 21200000: return 1
    if currentfrequency >= 28000000 and currentfrequency <= 28300000: return 1
        
    if currentfrequency > 3600000 and currentfrequency <= 400000:
        setfrequency(3530000)
        return 1

    if currentfrequency > 7125000 and currentfrequency <= 7300000:
        setfrequency(7030000)
        return 1

    if currentfrequency > 14150000 and currentfrequency <= 14350000:
        setfrequency(14030000)
        return 1

    if currentfrequency > 18068000 and currentfrequency <= 18110000:
        setfrequency(18070000)
        return 1

    if currentfrequency > 21200000 and currentfrequency <= 21450000:
        setfrequency(21030000)
        return 1

    if currentfrequency > 28300000 and currentfrequency <= 29700000:
        setfrequency(28030000)

    else:
        print("Frequency not in any known band")
        return None

    return None

def get_user_env_var(name: str, default: str | None = None):
    """
    Reads a Windows user-level environment variable straight from the registry,
    so it reflects the current persisted value even if this process started
    before the variable was last set.
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, name)
            return value
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        return default

def set_user_env_var(name: str, value: str):
    """
    Persists a Windows user-level environment variable and broadcasts
    WM_SETTINGCHANGE so newly launched processes pick it up without a
    logoff/logon.
    """
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)

    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A
    SMTO_ABORTIFHUNG = 0x0002
    result = ctypes.c_long()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
        SMTO_ABORTIFHUNG, 5000, ctypes.byref(result)
    )

def CapeCod():
    if checkdebug():
        print("\nCapeCod detected\n")
    set_user_env_var("LOCATION_VAR", "CAPECOD")
    return

def Charlotte():
    if checkdebug():
        print("\nCharlotte detected\n")
    set_user_env_var("LOCATION_VAR", "CHARLOTTE")
    return

# basic Full Tuning function for CW operation.  This will have to be fleshed out
# later to include SSB tuning operation, but for now it has about the same
# functionality as what the ft.py routine has in the old command project. 

def ft():
    if checkdebug():
        print("\nFull Tune detected\n")
    # Disable keyer, remove split, set power to 5W
    send_rig("W KR0; 0")        # Set KEYER to OFF
    send_rig("W BI1; 0")        # Set BREAK-IN to ON
    send_rig("W ST0; 0")        # Set SPLIT to OFF
    send_rig("W PC005; 0")      # Set POWER to 5

    input("Press Enter to continue...")

    # Enable keyer, set power to 100W
    send_rig("W KR1; 0")        # Set KEYER to ON
    send_rig("W AB; 0")         # Set VFOB to VFOA value
    send_rig("W PC100; 0")      # Set POWER to 100

def checkdebug() -> bool:
    """
    Reads the persisted DEBUG flag from the registry. Unlike a plain module
    global, this reflects setdebug()/unsetdebug() calls made in a prior,
    separate command-line invocation - each command is its own process, so
    an in-memory flag wouldn't survive between them.
    """
    return get_user_env_var("DEBUG", "0") == "1"

def setdebug():
    set_user_env_var("DEBUG", "1")
    return

def unsetdebug():
    set_user_env_var("DEBUG", "0")
    return