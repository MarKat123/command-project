import atexit
import socket
import winreg
import ctypes

_socket_handle = None
atexit.register(lambda: close_socket())

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

# ---------------------------------------------------------------------------
# Band plan: standard US amateur HF sub-band edges plus a default/calling
# frequency per band+mode segment. Edges are standard US allocations; the
# specific "default" frequencies were not independently confirmed against
# operator preference and are reasonable but arbitrary picks (common calling
# frequencies) -- review before relying on them operationally.
# 30m has no phone allocation, so it has a "cw" key only and sideband=None.
# Sideband: LSB below 10MHz (160/80/40m), USB at 10MHz+ (20/17/15/12/10m).
# ---------------------------------------------------------------------------
BAND_PLAN = {
    "160m": {
        "cw":  {"low": 1_800_000,  "high": 1_840_000,  "default": 1_810_000},
        "ssb": {"low": 1_840_000,  "high": 2_000_000,  "default": 1_900_000},
        "sideband": LSB_Mode,
    },
    "80m": {
        "cw":  {"low": 3_500_000,  "high": 3_600_000,  "default": 3_530_000},
        "ssb": {"low": 3_600_000,  "high": 4_000_000,  "default": 3_850_000},
        "sideband": LSB_Mode,
    },
    "40m": {
        "cw":  {"low": 7_000_000,  "high": 7_125_000,  "default": 7_030_000},
        "ssb": {"low": 7_125_000,  "high": 7_300_000,  "default": 7_225_000},
        "sideband": LSB_Mode,
    },
    "30m": {
        "cw":  {"low": 10_100_000, "high": 10_150_000, "default": 10_106_000},
        "sideband": None,   # no phone allocation on 30m
    },
    "20m": {
        "cw":  {"low": 14_000_000, "high": 14_150_000, "default": 14_030_000},
        "ssb": {"low": 14_150_000, "high": 14_350_000, "default": 14_250_000},
        "sideband": USB_Mode,
    },
    "17m": {
        "cw":  {"low": 18_068_000, "high": 18_110_000, "default": 18_086_000},
        "ssb": {"low": 18_110_000, "high": 18_168_000, "default": 18_130_000},
        "sideband": USB_Mode,
    },
    "15m": {
        "cw":  {"low": 21_000_000, "high": 21_200_000, "default": 21_030_000},
        "ssb": {"low": 21_200_000, "high": 21_450_000, "default": 21_300_000},
        "sideband": USB_Mode,
    },
    "12m": {
        "cw":  {"low": 24_890_000, "high": 24_930_000, "default": 24_910_000},
        "ssb": {"low": 24_930_000, "high": 24_990_000, "default": 24_950_000},
        "sideband": USB_Mode,
    },
    "10m": {
        "cw":  {"low": 28_000_000, "high": 28_300_000, "default": 28_030_000},
        "ssb": {"low": 28_300_000, "high": 29_700_000, "default": 28_400_000},
        "sideband": USB_Mode,
    },
}

# Max power per band (watts), driven by house RFI sensitivities that vary
# by band and aren't helped by choking the feed. Applied by pmax().
BAND_MAX_POWER = {
    "160m": 30,
    "80m":  60,
    "40m":  100,
    "30m":  80,
    "20m":  100,
    "17m":  100,
    "15m":  100,
    "12m":  100,
    "10m":  100,
}

"""
Following are the backbone commands for radio control
get_socket_handle() - returns the socket handle, opening it if not already open
close_socket() - cleanly close the socket when done
send_rig(cmd) - sends a command to the rig via TCP socket and returns the response
"""



SOCKET_TIMEOUT_SECONDS = 5.0

def get_socket_handle(host: str = 'localhost', port: int = 4532):
    """
    Returns the socket handle, opening it if not already open.
    Singleton pattern - only one socket opened for life of program.
    """
    global _socket_handle

    # Test if socket is already open and valid
    if _socket_handle is not None:
        try:
            # Send a zero-byte message to test if socket is still alive.
            # Note: this can pass even when the far end (rigctld, or its
            # COM port to the rig) has died silently without a clean
            # FIN/RST -- a zero-byte send doesn't push anything over the
            # wire that would surface a broken-pipe error. The timeout set
            # below is what actually catches that case, on the next real
            # send/recv.
            _socket_handle.send(b'')
            return _socket_handle  # Socket is good, return it
        except (socket.error, OSError):
            # Socket is dead, fall through to reopen it
            _socket_handle = None

    # Open the socket
    try:
        _socket_handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket_handle.settimeout(SOCKET_TIMEOUT_SECONDS)
        _socket_handle.connect((host, port))
        if checkdebug():
            print(f"Socket opened to {host}:{port}")
        return _socket_handle
    except socket.error as e:
        print(f"Failed to open socket: {e}")
        _socket_handle = None
        return None

def close_socket():
    """Cleanly close the socket when done. Registered with atexit (see
    below) so it runs at process exit regardless of which command ran --
    every command is its own short-lived process, so "at the end of each
    command" and "at process exit" are the same moment here."""
    global _socket_handle
    if _socket_handle is not None:
        try:
            _socket_handle.close()
        except socket.error as e:
            print(f"Error closing socket: {e}")
        finally:
            if checkdebug():
                print("Socket closed")
            _socket_handle = None

def send_rig(cmd: str):
    global _socket_handle
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

    except socket.timeout:
        print(f"Rig did not respond within {SOCKET_TIMEOUT_SECONDS}s -- "
              "check the COM port / rig power and connection")
        # Force socket to reopen next time
        _socket_handle = None
        return None

    except socket.error as e:
        print(f"Socket error sending command: {e}")
        # Force socket to reopen next time
        _socket_handle = None
        return None
"""
Basic commands for the radio
p5, p20, p40, p60, p80, p100 - set power levels
pmax - set power to the max allowed for the current band (BAND_MAX_POWER)
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

def pmax():
    """Sets power to the max allowed for whatever band VFO A is currently
    on, per BAND_MAX_POWER (house RFI sensitivities vary by band)."""
    if checkdebug():
        print("\npmax detected\n")
    currentfrequency = getfrequency()
    if currentfrequency is None:
        print("Failed to retrieve frequency")
        return None
    band = getBandForFrequency(currentfrequency)
    if band is None:
        print("Frequency not in any known band -- cannot determine max power")
        return None
    maxpower = BAND_MAX_POWER[band]
    if checkdebug():
        print(f"Band detected: {band}, setting max power to {maxpower}W")
    setpower(maxpower)
    return 1

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

#    MODE = "MD03", MONITOR = 10, SPEED = 24 WPM, BREAKIN = ON,
#    PC KEYING = RTS, PC KEYING CONTROL = ON, CW AUDIO TREBLE = 0, CW AUDIO MID = 0, CW AUDIO BASS = 0
#    PITCH = 550, BK-DELAY = 200
#
#    Applies the CW settings bundle only -- does not touch frequency.
#    VFO-A is asserted primary first, since this is where the operating
#    mode gets established -- if VFO-B were primary, the operator would
#    still be transmitting/receiving on VFO-B's stale settings even though
#    VFO-A now holds the new mode. Mode is set next, before KR/BI/ST (and
#    other CW-only settings), since those are rejected by the rig unless
#    it's already in CW mode (see ft()).
    if checkdebug():
        print("\nSet radio for CW operation\n")
    send_rig("W VS0; 0")        # Select VFO-A as primary
    send_rig("W MD03; 0")       # Set MODE to CW
    send_rig("W ML1010; 0")     # Set MONITOR to 10
    send_rig("W KS024; 0")      # Set KEY SPEED to 24 WPM
    send_rig("W BI1; 0")        # Set BREAK-IN to ON
    send_rig("W KR1; 0")        # Set KEYER to ON
    send_rig("W KP25; 0")       # Set PITCH to 550
    send_rig("W RF04; 0")       # Set ROOFING FILTER to 500Hz
    send_rig("W SH0007; 0")     # Set FILTER_WIDTH to 350Hz
    send_rig("W SS0520000; 0")  # Set PANADAPTER SPAN to 5kHz
    send_rig("W SS0640000; 0")  # Center the panadapter cursor
    # Scroll mode to CURSOR, with the (S) depth suffix -- per the CAT spec's
    # SS P2=6 table, (L)/(N)/(S) size the spectrum-scope area above the
    # waterfall, not the waterfall itself, so (S) = small scope area = the
    # waterfall gets MORE depth, not less. (S) here is deliberate for a
    # large waterfall, confirmed by hands-on experimentation on the rig.
    send_rig("W SS0680000; 0")  # Set scroll mode to CURSOR, large waterfall depth
    return "3"                  # the CW-U mode char, for VFO-B sync callers

def setSSB(band: str):
    """SSB settings bundle: selects the correct sideband (LSB/USB) for the
    given band via BAND_PLAN. Does not touch frequency. VFO-A is asserted
    primary first, for the same reason as setCW() -- mode is meaningless to
    the operator if VFO-B is what's actually active."""
    if checkdebug():
        print(f"\nSet radio for SSB operation on {band}\n")
    band_info = BAND_PLAN.get(band)
    if band_info is None or band_info.get("sideband") is None:
        print(f"No SSB allocation for band {band}")
        return None
    send_rig("W VS0; 0")        # Select VFO-A as primary
    modechar = band_info["sideband"][-1]
    setmode(modechar)
    send_rig("W SS0540000; 0")  # Set PANADAPTER SPAN to 20kHz
    send_rig("W SS0640000; 0")  # Center the panadapter cursor
    # Scroll mode to CURSOR, with the (S) depth suffix -- per the CAT spec's
    # SS P2=6 table, (L)/(N)/(S) size the spectrum-scope area above the
    # waterfall, not the waterfall itself, so (S) = small scope area = the
    # waterfall gets MORE depth, not less. (S) here is deliberate for a
    # large waterfall, confirmed by hands-on experimentation on the rig.
    send_rig("W SS0680000; 0")  # Set scroll mode to CURSOR, large waterfall depth
    return modechar             # for VFO-B sync callers

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

    digits = "".join(filter(str.isdigit, frequencystring))
    if not digits:
        print(f"Malformed frequency response: {frequencystring!r}")
        return None

    if checkdebug():
        print(f"Frequency received: {frequencystring}")
        print(f"Frequency integer: {digits}")

    return int(digits)

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

def getmode():
    if checkdebug():
        print("\nGet mode detected\n")
    modestring = send_rig("W MD0; 5")
    if modestring is None or len(modestring) < 4:
        print("Failed to retrieve mode")
        return None
    if checkdebug():
        print(f"Mode received: {modestring}")
    return modestring[3]   # the X in "MD0X;"

def setmode(modechar: str):
    if checkdebug():
        print(f"\nSet mode cmd  W MD0{modechar}; 0\n")
    send_rig(f"W MD0{modechar}; 0")
    return

def setmodeB(modechar: str):
    """Sets VFO-B's mode directly via W MD1X. Turns out "W AB; 0" (VFOB=VFOA)
    copies mode as well as frequency, as long as VFOA already holds the
    final target mode at the moment AB fires (see ft(), which sequences its
    closing AB after restoring VFOA's mode for exactly this reason) -- so
    this explicit setter is currently unused by any caller. Kept around
    rather than deleted in case a future caller needs to set VFO-B's mode
    without going through a VFOA-mediated AB copy."""
    if checkdebug():
        print(f"\nSet VFO-B mode cmd  W MD1{modechar}; 0\n")
    send_rig(f"W MD1{modechar}; 0")
    return

def getpower():
    if checkdebug():
        print("\nGet power detected\n")
    powerstring = send_rig("W PC; 6")
    if powerstring is None or len(powerstring) < 5 or not powerstring[2:5].isdigit():
        print(f"Malformed power response: {powerstring!r}")
        return None
    if checkdebug():
        print(f"Power received: {powerstring}")
    return int(powerstring[2:5])

def setpower(watts: int):
    if checkdebug():
        print(f"\nSet power cmd  W PC{str(watts).zfill(3)}; 0\n")
    send_rig(f"W PC{str(watts).zfill(3)}; 0")
    return

def test():
    if checkdebug():
        print("\nTest function detected\n")
#        junk = test2()  # unused for now, but will be useful for future debug and testing
#        print("\nTest2 returned: ", junk, "\n")
        return 43

def getBandForFrequency(frequency: int):
    """Reverse-lookup: which BAND_PLAN band (if any) a frequency falls
    into, checking both its cw and ssb segments."""
    for band, info in BAND_PLAN.items():
        for mode_key in ("cw", "ssb"):
            segment = info.get(mode_key)
            if segment and segment["low"] <= frequency <= segment["high"]:
                return band
    return None

def setBandModeFrequency(band: str, mode: str):
    """Move VFO A to the default/calling frequency for band+mode, per
    BAND_PLAN. Always jumps to the known default rather than trying to
    preserve the current frequency -- there's no reason to preserve
    position in a band you're deliberately switching into."""
    if checkdebug():
        print(f"\nSetting frequency for {band} {mode}\n")
    target = BAND_PLAN[band][mode]["default"]
    setfrequency(target)
    return 1

def tuneBand(band: str, mode: str):
    """Shared implementation behind every t<band>c()/t<band>s() command:
    move to that segment's default frequency FIRST, then apply the mode
    settings (setCW()/setSSB() center the panadapter cursor on the current
    frequency -- doing this before the frequency change left the cursor
    centered on the old frequency, not the new one), copy VFO A to VFO B,
    cap power for the band (pmax()), then run ft() to put the rig in
    tune-ready state. ft() reads back whatever mode/power was just set here
    as its "original" state, so declining to key the paddle and just
    pressing Enter leaves the rig exactly on the band/mode/power just
    selected -- actually tuning the antenna is still an operator choice
    (paddle down or not), not automatic."""
    if checkdebug():
        print(f"\ntuneBand band={band} mode={mode} detected\n")

    if mode not in ("cw", "ssb"):
        print(f"Unknown mode: {mode}")
        return None

    setBandModeFrequency(band, mode)

    if mode == "cw":
        modechar = setCW()
    else:
        modechar = setSSB(band)
        if modechar is None:
            return None

    send_rig("W AB; 0")         # Set VFOB to VFOA value
    pmax()                       # Cap power for this band before tuning
    ft()
    return 1

# ---------------------------------------------------------------------------
# Band/mode tune commands: t<band>c()/t<band>s() move the rig to that
# band's CW or SSB default frequency, apply the corresponding mode settings,
# and run ft() (see tuneBand()) to leave the rig in tune-ready state. Press
# Enter without keying the paddle to skip actually tuning the antenna.
# ---------------------------------------------------------------------------
def t160c():
    if checkdebug():
        print("\nt160c detected\n")
    return tuneBand("160m", "cw")

def t160s():
    if checkdebug():
        print("\nt160s detected\n")
    return tuneBand("160m", "ssb")

def t80c():
    if checkdebug():
        print("\nt80c detected\n")
    return tuneBand("80m", "cw")

def t80s():
    if checkdebug():
        print("\nt80s detected\n")
    return tuneBand("80m", "ssb")

def t40c():
    if checkdebug():
        print("\nt40c detected\n")
    return tuneBand("40m", "cw")

def t40s():
    if checkdebug():
        print("\nt40s detected\n")
    return tuneBand("40m", "ssb")

def t30c():
    if checkdebug():
        print("\nt30c detected\n")
    return tuneBand("30m", "cw")

def t20c():
    if checkdebug():
        print("\nt20c detected\n")
    return tuneBand("20m", "cw")

def t20s():
    if checkdebug():
        print("\nt20s detected\n")
    return tuneBand("20m", "ssb")

def t17c():
    if checkdebug():
        print("\nt17c detected\n")
    return tuneBand("17m", "cw")

def t17s():
    if checkdebug():
        print("\nt17s detected\n")
    return tuneBand("17m", "ssb")

def t15c():
    if checkdebug():
        print("\nt15c detected\n")
    return tuneBand("15m", "cw")

def t15s():
    if checkdebug():
        print("\nt15s detected\n")
    return tuneBand("15m", "ssb")

def t12c():
    if checkdebug():
        print("\nt12c detected\n")
    return tuneBand("12m", "cw")

def t12s():
    if checkdebug():
        print("\nt12s detected\n")
    return tuneBand("12m", "ssb")

def t10c():
    if checkdebug():
        print("\nt10c detected\n")
    return tuneBand("10m", "cw")

def t10s():
    if checkdebug():
        print("\nt10s detected\n")
    return tuneBand("10m", "ssb")

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
    set_user_env_var("RIG_COM", "COM7")
    return

def Charlotte():
    if checkdebug():
        print("\nCharlotte detected\n")
    set_user_env_var("LOCATION_VAR", "CHARLOTTE")
    set_user_env_var("RIG_COM", "COM5")
    return

# Full Tuning function. Mode-agnostic: reads the rig's current mode/power
# before touching anything, forces CW-U (required for the paddle's tuner
# keydown tone) and low power for the actual tune, then restores exactly
# what was there on entry. Safe to call from CW or SSB (or any other mode).

def ft():
    if checkdebug():
        print("\nFull Tune detected\n")

    original_mode = getmode()
    original_power = getpower()
    if original_mode is None or original_power is None:
        print("Failed to read current radio state — aborting Full Tune")
        return None

    # Enter tuning state: keyer off, break-in on, split off, force CW-U,
    # power to 5W. VFO-A-primary is NOT asserted here -- that's now the
    # calling routine's job (setCW()/setSSB(), where the mode is actually
    # established) since ft() is a general-purpose service function that
    # should work on whatever VFO-A already holds, not silently override
    # VFO selection on every standalone call.
    setmode("3")                # Force CW-U (required for tuner keydown tone)
    send_rig("W KR0; 0")        # Set KEYER to OFF
    send_rig("W BI1; 0")        # Set BREAK-IN to ON
    send_rig("W ST0; 0")        # Set SPLIT to OFF
    setpower(5)                 # Set POWER to 5W

    input("Press Enter to continue...")

    # Exit tuning state: keyer back on, VFO-A stays primary (never exit with
    # VFO-B selected), restore original mode, THEN sync VFOB -- AB copies
    # mode as well as frequency, so it must fire after the mode restore or
    # VFOB ends up stuck in the CW-U tuning mode instead of the real target
    # mode. Restore power last (unaffected by AB either way).
    send_rig("W KR1; 0")        # Set KEYER to ON
    send_rig("W VS0; 0")        # Re-assert VFO-A as primary
    setmode(original_mode)      # Restore original mode
    send_rig("W AB; 0")         # Set VFOB to VFOA value (mode + frequency)
    setpower(original_power)    # Restore original power
    return 1

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