#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root" >&2
  exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
lab_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y acl attr auditd audispd-plugins aide apparmor-utils libpam-pwquality libpwquality-tools nftables

if [ ! -e /etc/pam.d/common-auth.pre-paszi-lab1 ]; then
  cp -a /etc/pam.d/common-auth /etc/pam.d/common-auth.pre-paszi-lab1
fi
if [ ! -e /etc/pam.d/common-password.pre-paszi-lab1 ]; then
  cp -a /etc/pam.d/common-password /etc/pam.d/common-password.pre-paszi-lab1
fi
# Удаление ранее добавленного вручную дублирующего блока. Стандартный стек
# Debian после этого воспроизводимо формирует pam-auth-update.
sed -i \
  '/^auth required pam_faillock\.so preauth silent deny=5 unlock_time=600$/,/^auth \[default=die\] pam_faillock\.so authsucc$/d' \
  /etc/pam.d/common-auth
pam-auth-update --force

install -D -m 0644 "$lab_dir/config/pwquality.conf" /etc/security/pwquality.conf.d/99-paszi-lab1.conf
install -D -m 0644 "$lab_dir/config/journald.conf" /etc/systemd/journald.conf.d/99-paszi-lab1.conf
install -D -m 0644 "$lab_dir/config/audit.rules" /etc/audit/rules.d/99-paszi-lab1.rules
install -D -m 0644 "$lab_dir/config/sshd.conf" /etc/ssh/sshd_config.d/99-paszi-lab1.conf
install -D -m 0644 "$lab_dir/config/aide.conf" /etc/aide/paszi-lab1.conf

getent group paszi_readers >/dev/null || groupadd --system paszi_readers
getent group paszi_editors >/dev/null || groupadd --system paszi_editors

for account in paszi_reader paszi_writer paszi_denied; do
  id "$account" >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin "$account"
done
usermod -a -G paszi_readers paszi_reader
usermod -a -G paszi_editors paszi_writer

install -d -o root -g paszi_editors -m 2770 /srv/paszi-lab1/protected
printf '%s\n' 'Учебные защищаемые данные ПАСЗИ' > /srv/paszi-lab1/protected/sample.txt
chown root:paszi_editors /srv/paszi-lab1/protected/sample.txt
chmod 0640 /srv/paszi-lab1/protected/sample.txt
setfacl -m g::rwx,g:paszi_readers:r-x,m:rwx /srv/paszi-lab1/protected
setfacl -m d:g:paszi_readers:r-x,d:g:paszi_editors:rwx,d:m:rwx /srv/paszi-lab1/protected
setfacl -m g::rw-,g:paszi_readers:r--,m:rw /srv/paszi-lab1/protected/sample.txt
setfattr -n user.confidentiality -v confidential /srv/paszi-lab1/protected
setfattr -n user.confidentiality -v confidential /srv/paszi-lab1/protected/sample.txt

mkdir -p /var/log/journal
systemd-tmpfiles --create --prefix /var/log/journal
systemctl restart systemd-journald

sshd -t
systemctl reload ssh

systemctl enable --now apparmor
augenrules --load
systemctl enable auditd >/dev/null 2>&1 || true
systemctl restart auditd 2>/dev/null || service auditd restart

nft -c -f "$lab_dir/config/nftables.conf"
install -m 0644 "$lab_dir/config/nftables.conf" /etc/nftables.conf
systemctl enable --now nftables

rm -f /var/lib/aide/paszi-lab1.db.new
aide --config=/etc/aide/paszi-lab1.conf --init
mv /var/lib/aide/paszi-lab1.db.new /var/lib/aide/paszi-lab1.db

backup_dir=/var/backups/paszi-lab1
install -d -m 0700 "$backup_dir"
tar -czf "$backup_dir/security-config.tar.gz" \
  /etc/pam.d \
  /etc/security/pwquality.conf.d/99-paszi-lab1.conf \
  /etc/audit/rules.d/99-paszi-lab1.rules \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d/99-paszi-lab1.conf \
  /etc/systemd/journald.conf.d/99-paszi-lab1.conf \
  /etc/nftables.conf /etc/aide/paszi-lab1.conf \
  /var/lib/aide/paszi-lab1.db
cp "$backup_dir/security-config.tar.gz" /home/user/paszi-lab1-security-config.tar.gz
chown user:user /home/user/paszi-lab1-security-config.tar.gz
chmod 0600 /home/user/paszi-lab1-security-config.tar.gz

echo "Configuration completed"
