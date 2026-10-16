# firewalld — apply on shop hosts (webapp01 / webapp02)
#
# Public (VIP / internet):
#   firewall-cmd --permanent --add-service=http
#   firewall-cmd --permanent --add-service=https   # when TLS is enabled
#
# From the 10.10.4.0/24 lab LAN (peer HAProxy health checks, Galera, LDAP):
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.0/24 port port="8080" protocol=tcp accept'
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.0/24 port port="8010-8013" protocol=tcp accept'
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.0/24 port port="8001" protocol=tcp accept'
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.0/24 port port="3306" protocol=tcp accept'
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.0/24 port port="4444" protocol=tcp accept'
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.0/24 port port="4567-4568" protocol=tcp accept'
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.0/24 port port="389" protocol=tcp accept'
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.0/24 port port="636" protocol=tcp accept'
#
# api-stats :8014 only from second-demo:
#   firewall-cmd --permanent --zone=public --add-rich-rule='rule family=ipv4 source address=10.10.4.110 port port="8014" protocol=tcp accept'
#
# VRRP:
#   firewall-cmd --permanent --add-rich-rule='rule protocol value="vrrp" accept'
#   firewall-cmd --permanent --add-port=112/udp
#
# firewall-cmd --reload
#
# On second-demo: allow 80/tcp (dashboard) and Galera 4567 from 10.10.4.0/24.
