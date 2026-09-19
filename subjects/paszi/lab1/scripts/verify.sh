#!/bin/sh
set -eu

section() {
  printf '\n===== %s =====\n' "$1"
}

check() {
  name=$1
  shift
  if "$@"; then
    printf 'PASS: %s\n' "$name"
  else
    printf 'FAIL: %s\n' "$name"
    failures=$((failures + 1))
  fi
}

failures=0

section "Система"
date --iso-8601=seconds
grep '^PRETTY_NAME=' /etc/os-release
uname -srmo
systemd-detect-virt 2>/dev/null || true

section "Службы"
for service in ssh auditd apparmor nftables systemd-journald; do
  check "$service active" systemctl is-active --quiet "$service"
done

section "Парольная аутентификация"
grep -n 'pam_pwquality.so' /etc/pam.d/common-password || true
cat /etc/security/pwquality.conf.d/99-paszi-lab1.conf
check "PAM uses pam_pwquality" grep -q 'pam_pwquality.so' /etc/pam.d/common-password
check "pwquality accepts compliant test password" sh -c "printf '%s\n' 'CorrectHorse7' | pwscore >/dev/null"
if printf '%s\n' 'short' | pwscore >/dev/null 2>&1; then
  printf 'FAIL: pwquality rejects short test password\n'
  failures=$((failures + 1))
else
  printf 'PASS: pwquality rejects short test password\n'
fi

section "Контроль целостности до тестового изменения"
check "AIDE baseline exists" test -s /var/lib/aide/paszi-lab1.db
check "AIDE baseline initially matches" aide --config=/etc/aide/paszi-lab1.conf --check

section "Матрица доступа и маркировка"
getfacl -p /srv/paszi-lab1/protected
getfacl -p /srv/paszi-lab1/protected/sample.txt
getfattr -d -m user.confidentiality /srv/paszi-lab1/protected /srv/paszi-lab1/protected/sample.txt
check "reader can read" runuser -u paszi_reader -- cat /srv/paszi-lab1/protected/sample.txt
check "writer can append" runuser -u paszi_writer -- sh -c "printf '%s\n' 'Проверка записи' >> /srv/paszi-lab1/protected/sample.txt"
if runuser -u paszi_denied -- cat /srv/paszi-lab1/protected/sample.txt >/dev/null 2>&1; then
  printf 'FAIL: unrelated subject is denied\n'
  failures=$((failures + 1))
else
  printf 'PASS: unrelated subject is denied\n'
fi

section "SSH"
sshd -t
sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|maxauthtries|x11forwarding) '
check "root SSH login disabled" sh -c "sshd -T | grep -qx 'permitrootlogin no'"
check "SSH password authentication disabled" sh -c "sshd -T | grep -qx 'passwordauthentication no'"

section "Аудит"
auditctl -s
auditctl -l
check "identity audit rule loaded" sh -c "auditctl -l | grep -q -- '-k identity'"
check "protected directory audit rule loaded" sh -c "auditctl -l | grep -q -- '-k protected_data'"
ausearch -if /var/log/audit/audit.log -k protected_data -sv no -i 2>/dev/null | tail -30 || true

section "Межсетевой экран"
nft list ruleset
check "nftables input policy is drop" sh -c "nft list chain inet paszi_filter input | grep -q 'policy drop'"
check "SSH limited to UTM subnet" sh -c "nft list chain inet paszi_filter input | grep -q '192.168.64.0/24.*tcp dport 22.*accept'"

section "AppArmor"
aa-status || true
check "AppArmor kernel module enabled" grep -qx Y /sys/module/apparmor/parameters/enabled

section "Обнаружение изменения средствами AIDE"
aide_diff=/tmp/paszi-lab1-aide-diff.txt
if aide --config=/etc/aide/paszi-lab1.conf --check >"$aide_diff" 2>&1; then
  echo "FAIL: AIDE detects the controlled file change"
  failures=$((failures + 1))
elif grep -q 'Changed entries:' "$aide_diff"; then
  echo "PASS: AIDE detects the controlled file change"
else
  cat "$aide_diff"
  echo "FAIL: AIDE check failed without a reported changed entry"
  failures=$((failures + 1))
fi
grep -E '^(Changed entries:|  [cf]:|File:)' "$aide_diff" | head -20 || true

rm -f /var/lib/aide/paszi-lab1.db.new
aide --config=/etc/aide/paszi-lab1.conf --init >/dev/null
mv /var/lib/aide/paszi-lab1.db.new /var/lib/aide/paszi-lab1.db
check "AIDE baseline updated and clean" aide --config=/etc/aide/paszi-lab1.conf --check

section "Восстановление"
sha256sum /var/backups/paszi-lab1/security-config.tar.gz /home/user/paszi-lab1-security-config.tar.gz
check "first backup exists" test -s /var/backups/paszi-lab1/security-config.tar.gz
check "second backup exists" test -s /home/user/paszi-lab1-security-config.tar.gz
check "backup copies match" cmp -s /var/backups/paszi-lab1/security-config.tar.gz /home/user/paszi-lab1-security-config.tar.gz

section "Итог"
if [ "$failures" -eq 0 ]; then
  echo "ALL IMPLEMENTED CHECKS PASSED"
else
  printf '%s check(s) failed\n' "$failures"
  exit 1
fi
