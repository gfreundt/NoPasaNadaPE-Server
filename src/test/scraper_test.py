import subprocess
import time

OVPN_CONFIG = "/etc/openvpn/client/pe-lim.prod.surfshark.com_udp.ovpn"


def vpn_on():
    """
    Starts the OpenVPN connection in daemon mode.
    Requires sudo privileges.
    """
    subprocess.run(["sudo", "openvpn", "--config", OVPN_CONFIG, "--daemon"], check=True)

    time.sleep(2)


def vpn_off():
    """
    Stops all running OpenVPN processes.
    Requires sudo privileges.
    """
    subprocess.run(["sudo", "pkill", "openvpn"], check=False)


def print_public_ip():
    """
    Prints the current public IPv4 address.
    """
    result = subprocess.run(
        ["curl", "-4", "-s", "ifconfig.me"], capture_output=True, text=True, check=True
    )

    print(result.stdout.strip())


def vpn_is_online():
    """
    Returns True if an OpenVPN process is running, False otherwise.
    """
    result = subprocess.run(
        ["pgrep", "-x", "openvpn"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    return result.returncode == 0


print("ip", print_public_ip)
print("online", vpn_is_online())
print("on", vpn_on())
time.sleep(5)
print("ip", print_public_ip)
print("online", vpn_is_online())
print("off", vpn_off())
time.sleep(5)
print("ip", print_public_ip)
print("online", vpn_is_online())
print("on", vpn_on())
