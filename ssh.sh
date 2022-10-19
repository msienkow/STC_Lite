#!/bin/sh
sudo echo "TCPKeepAlive no" >> /etc/ssh/sshd_config
sudo echo "ClientAliveInterval 30" >> /etc/ssh/sshd_config
sudo echo "ClientAliveCountMax 60" >> /etc/ssh/sshd_config