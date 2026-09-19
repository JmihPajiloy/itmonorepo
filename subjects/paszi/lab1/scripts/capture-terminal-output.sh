#!/bin/sh
set -eu

output_dir=${1:-/tmp/paszi-terminal-output}
install -d -m 0755 "$output_dir"

{
  printf '%s\n' '$ cat /etc/os-release | head -6'
  head -6 /etc/os-release
  printf '\n%s\n' '$ uname -srmo'
  uname -srmo
  printf '\n%s\n' '$ systemd-detect-virt'
  systemd-detect-virt
  printf '\n%s\n' '$ hostname -I'
  hostname -I
} > "$output_dir/01-system.txt"

{
  printf '%s\n' '$ sudo getfacl -p /srv/paszi-lab1/protected/sample.txt'
  getfacl -p /srv/paszi-lab1/protected/sample.txt
  printf '\n%s\n' '$ sudo getfattr -d -m user.confidentiality /srv/paszi-lab1/protected/sample.txt'
  getfattr --absolute-names -d -m user.confidentiality /srv/paszi-lab1/protected/sample.txt
  printf '\n%s\n' '$ sudo runuser -u paszi_reader -- cat /srv/paszi-lab1/protected/sample.txt | head -1'
  runuser -u paszi_reader -- cat /srv/paszi-lab1/protected/sample.txt | head -1
  printf '\n%s\n' '$ sudo runuser -u paszi_denied -- cat /srv/paszi-lab1/protected/sample.txt'
  if runuser -u paszi_denied -- cat /srv/paszi-lab1/protected/sample.txt 2>&1; then
    echo 'ERROR: access unexpectedly allowed'
  else
    echo 'ACCESS DENIED: expected result'
  fi
} > "$output_dir/02-access.txt"

{
  printf '%s\n' '$ systemctl is-active ssh auditd apparmor nftables systemd-journald'
  systemctl is-active ssh auditd apparmor nftables systemd-journald
  printf '\n%s\n' '$ sudo sshd -T | grep -E "^(permitrootlogin|passwordauthentication|maxauthtries) "'
  sshd -T | grep -E '^(permitrootlogin|passwordauthentication|maxauthtries) '
  printf '\n%s\n' '$ sudo nft list chain inet paszi_filter input'
  nft list chain inet paszi_filter input
} > "$output_dir/03-services-network.txt"

{
  printf '%s\n' '$ sudo auditctl -l | grep -E "identity|protected_data|privileged_exec"'
  auditctl -l | grep -E 'identity|protected_data|privileged_exec'
  printf '\n%s\n' '$ sudo aide --config=/etc/aide/paszi-lab1.conf --check | head -8'
  aide --config=/etc/aide/paszi-lab1.conf --check | head -8
  printf '\n%s\n' '$ sha256sum /var/backups/paszi-lab1/security-config.tar.gz /home/user/paszi-lab1-security-config.tar.gz'
  sha256sum /var/backups/paszi-lab1/security-config.tar.gz /home/user/paszi-lab1-security-config.tar.gz
  printf '\n%s\n' '$ sudo /tmp/paszi-lab1/scripts/verify.sh | tail -3'
  /tmp/paszi-lab1/scripts/verify.sh | tail -3
} > "$output_dir/04-audit-integrity.txt"

chmod 0644 "$output_dir"/*.txt
