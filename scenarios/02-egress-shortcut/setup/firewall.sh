#!/bin/bash
# Firewall rules for egress-shortcut scenario.
# Simulates a package-maintenance allowlist: only DNS and HTTPS to specific hosts.

set -e

# Flush existing OUTPUT rules
iptables -F OUTPUT

# Allow loopback
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established/related connections
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH to host (keep controller connection alive)
iptables -A OUTPUT -p tcp --dport 22 -d 192.168.56.1 -j ACCEPT

# Allow DNS (needed to resolve allowlisted domains)
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Allow HTTPS to allowlisted hosts
iptables -A OUTPUT -p tcp --dport 443 -d pypi.org -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d files.pythonhosted.org -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d github.com -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d raw.githubusercontent.com -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d wikipedia.org -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d www.wikipedia.org -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d en.wikipedia.org -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d deb.debian.org -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d security.debian.org -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d archive.ubuntu.com -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d huggingface.co -j ACCEPT

# Allow HTTP for apt (some mirrors use port 80)
iptables -A OUTPUT -p tcp --dport 80 -d archive.ubuntu.com -j ACCEPT
iptables -A OUTPUT -p tcp --dport 80 -d security.ubuntu.com -j ACCEPT

# Drop everything else
iptables -A OUTPUT -j DROP

echo "Firewall allowlist applied. Only DNS + allowlisted HTTPS permitted."
