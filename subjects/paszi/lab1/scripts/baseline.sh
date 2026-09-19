#!/bin/sh
set -eu

section() {
  printf '\n===== %s =====\n' "$1"
}

section "Дата и узел"
date --iso-8601=seconds
hostnamectl 2>/dev/null || true
ip -brief address 2>/dev/null || true

section "Операционная система"
cat /etc/os-release
uname -a
dpkg --print-architecture
systemd-detect-virt 2>/dev/null || true

section "Учетные записи и полномочия"
id
getent group sudo || true
sudo -n id

section "Службы до настройки"
for service in ssh auditd apparmor nftables systemd-journald; do
  printf '%-18s ' "$service"
  systemctl is-active "$service" 2>/dev/null || true
done

section "Установленные защитные пакеты"
dpkg-query -W -f='${binary:Package}\t${Version}\n' \
  openssh-server apparmor apparmor-utils auditd aide libpam-pwquality acl attr nftables \
  2>/dev/null || true

section "AppArmor"
cat /sys/module/apparmor/parameters/enabled 2>/dev/null || true
sudo -n aa-status 2>/dev/null || true

section "PAM и политика паролей"
grep -nE 'pam_(unix|pwquality|faillock)\.so' /etc/pam.d/common-auth /etc/pam.d/common-password \
  2>/dev/null || true
grep -RnhE '^(minlen|ucredit|lcredit|dcredit|difok|retry)[[:space:]]*=' \
  /etc/security/pwquality.conf /etc/security/pwquality.conf.d 2>/dev/null || true

section "SSH"
sudo -n sshd -T 2>/dev/null | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|maxauthtries|x11forwarding) ' || true

section "Аудит"
sudo -n auditctl -s 2>/dev/null || true
sudo -n auditctl -l 2>/dev/null || true

section "Межсетевой экран"
sudo -n nft list ruleset 2>/dev/null || true

section "Защищаемый каталог"
ls -ld /srv/paszi-lab1/protected 2>/dev/null || true
getfacl -p /srv/paszi-lab1/protected 2>/dev/null || true

