#!/usr/bin/env bash
# Dedicated Ubuntu VM only. Requires a tested key, an explicit management subnet,
# and SSH_CONNECTION preserved by the calling sudo command.
set -euo pipefail
[[ $EUID == 0 && $# == 3 ]] || { echo 'Usage: sudo env SSH_CONNECTION="$SSH_CONNECTION" bash harden-host.sh USER ADMIN_CIDR NPM_IP'; exit 2; }
operator=$1; admin_cidr=$2; npm_ip=$3
python3 - "$operator" "$admin_cidr" "$npm_ip" "${SSH_CONNECTION%% *}" <<'PY'
import ipaddress,re,sys
assert re.fullmatch('[a-z_][a-z0-9_-]*',sys.argv[1])
network=ipaddress.ip_network(sys.argv[2]); assert network.version == 4
assert ipaddress.ip_address(sys.argv[3]).version == 4
assert ipaddress.ip_address(sys.argv[4]) in network, 'Current SSH peer must remain allowed'
PY
operator_home=$(getent passwd "$operator" | cut -d: -f6)
[[ -s "$operator_home/.ssh/authorized_keys" ]] || { echo 'A verified SSH key is required'; exit 1; }
interface=$(ip -4 route get "$npm_ip" | awk '{for(i=1;i<=NF;i++) if($i=="dev") {print $(i+1);exit}}')
[[ $interface =~ ^[a-zA-Z0-9_.:-]+$ ]]
iptables -w -S DOCKER-USER >/dev/null
state=/var/lib/nextcloud-bridge/hardening
dropin=/etc/ssh/sshd_config.d/00-nextcloud-hardening.conf
[[ ! -e "$state" && ! -e "$dropin" && ! -e /usr/local/sbin/nextcloud-firewall ]] || { echo 'Existing hardening files: inspect before rerunning'; exit 1; }
install -d -m 0700 "$state"
iptables-save > "$state/iptables-before.txt"
ip6tables-save > "$state/ip6tables-before.txt"
/usr/sbin/sshd -T > "$state/sshd-before.txt"
cat > /usr/local/sbin/nextcloud-firewall <<EOF
#!/bin/bash
set -euo pipefail
iptables -w -N NC-HOST 2>/dev/null || true
iptables -w -F NC-HOST
iptables -w -A NC-HOST -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
iptables -w -A NC-HOST -i lo -j RETURN
iptables -w -A NC-HOST -p tcp --dport 22 -s $admin_cidr -j RETURN
iptables -w -A NC-HOST -p tcp --dport 22 -j DROP
iptables -w -A NC-HOST -p tcp -m multiport --dports 8081,8082 -s $npm_ip -j RETURN
iptables -w -A NC-HOST -p tcp -m multiport --dports 8081,8082 -j DROP
iptables -w -C INPUT -j NC-HOST 2>/dev/null || iptables -w -I INPUT 1 -j NC-HOST
iptables -w -N NC-CONTAINERS 2>/dev/null || true
iptables -w -F NC-CONTAINERS
iptables -w -A NC-CONTAINERS -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
iptables -w -A NC-CONTAINERS -i $interface -s $npm_ip -p tcp -m multiport --dports 8081,8082 -j RETURN
iptables -w -A NC-CONTAINERS -i $interface -j DROP
iptables -w -C DOCKER-USER -j NC-CONTAINERS 2>/dev/null || iptables -w -I DOCKER-USER 1 -j NC-CONTAINERS
ip6tables -w -N NC-HOST6 2>/dev/null || true
ip6tables -w -F NC-HOST6
ip6tables -w -A NC-HOST6 -i lo -j RETURN
ip6tables -w -A NC-HOST6 -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
ip6tables -w -A NC-HOST6 -p tcp -m multiport --dports 22,8081,8082 -j DROP
ip6tables -w -C INPUT -j NC-HOST6 2>/dev/null || ip6tables -w -I INPUT 1 -j NC-HOST6
EOF
chmod 0700 /usr/local/sbin/nextcloud-firewall
cat > /usr/local/sbin/nextcloud-hardening-rollback <<'EOF'
#!/bin/bash
set -u
systemctl disable nextcloud-firewall.service 2>/dev/null || true
iptables -w -D INPUT -j NC-HOST 2>/dev/null || true
iptables -w -D DOCKER-USER -j NC-CONTAINERS 2>/dev/null || true
ip6tables -w -D INPUT -j NC-HOST6 2>/dev/null || true
rm -f /etc/ssh/sshd_config.d/00-nextcloud-hardening.conf
/usr/sbin/sshd -t && systemctl reload ssh
echo 'Custom SSH/firewall hardening rolled back; prior rules retained.'
EOF
chmod 0700 /usr/local/sbin/nextcloud-hardening-rollback
cat > /etc/systemd/system/nextcloud-firewall.service <<'EOF'
[Unit]
Description=Nextcloud VM ingress restrictions
After=docker.service network-online.target
Requires=docker.service
PartOf=docker.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/nextcloud-firewall
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
confirmation="$operator_home/.local/share/nextcloud-bridge-setup/hardening-confirmed"
rm -f -- "$confirmation"
systemd-run --unit=nextcloud-hardening-rollback --on-active=10m /usr/local/sbin/nextcloud-hardening-rollback
trap '/usr/local/sbin/nextcloud-hardening-rollback' ERR
cat > "$dropin" <<EOF
PermitRootLogin no
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
PermitTunnel no
MaxAuthTries 3
LoginGraceTime 30
MaxSessions 4
AllowUsers $operator
EOF
/usr/sbin/sshd -t
systemctl enable --now nextcloud-firewall.service
systemctl reload ssh
echo 'Hardening applied. Automatic rollback in ten minutes unless a NEW key SSH connection and public endpoints are verified.'
echo "After successful checks, the operator must create: $confirmation"
for attempt in $(seq 1 240); do
    if [[ -f "$confirmation" ]]; then
        systemctl stop nextcloud-hardening-rollback.timer
        /usr/sbin/sshd -T > "$state/sshd-after.txt"
        iptables-save > "$state/iptables-after.txt"
        ip6tables-save > "$state/ip6tables-after.txt"
        touch "$state/verified"
        echo 'HOST_HARDENING_VERIFIED; automatic rollback cancelled.'
        exit 0
    fi
    sleep 2
done
/usr/local/sbin/nextcloud-hardening-rollback
exit 1
