#!/usr/bin/env bash
# Close the model API (8000, Docker-published) and the tool server (9000, host process)
# to the venue network. Loopback and Docker/OpenShell bridges stay open.
#   sudo scripts/setup/04_lockdown_ports.sh          apply (idempotent)
#   sudo scripts/setup/04_lockdown_ports.sh status   show rules
#   sudo scripts/setup/04_lockdown_ports.sh remove   undo
# Rules are lost on reboot or Docker restart: re-run after either.
set -euo pipefail
source "$(dirname "$0")/../env.sh"
[[ $EUID -eq 0 ]] || die "run with sudo"

mode="${1:-apply}"
rules=()
for i in $(uplink_ifaces); do
  # ufw does not see Docker-published ports; DOCKER-USER does.
  rules+=("iptables DOCKER-USER -i $i -p tcp --dport $VLLM_PORT -j DROP")
  # docker-proxy may listen on [::]:8000; the tool server is a host process. Both go through INPUT.
  rules+=("ip6tables INPUT -i $i -p tcp --dport $VLLM_PORT -j DROP")
  rules+=("iptables INPUT -i $i -p tcp --dport $TOOLSERVER_PORT -j DROP")
  rules+=("ip6tables INPUT -i $i -p tcp --dport $TOOLSERVER_PORT -j DROP")
done

for r in "${rules[@]}"; do
  read -r cmd chain spec <<<"$r"
  case "$mode" in
    apply)  if $cmd -C $chain $spec 2>/dev/null; then echo "  present  $r"
            else $cmd -I $chain $spec && echo "  added    $r"; fi ;;
    remove) while $cmd -C $chain $spec 2>/dev/null; do $cmd -D $chain $spec; done; echo "  removed  $r" ;;
    status) if $cmd -C $chain $spec 2>/dev/null; then echo "  ON   $r"; else echo "  off  $r"; fi ;;
    *) die "usage: $0 [apply|status|remove]" ;;
  esac
done

[[ "$mode" == apply ]] && say "test from another laptop on the venue network (should time out):
  curl -m 3 http://$(ip -4 -o addr show "$(uplink_ifaces | head -1)" | awk '{print $4}' | cut -d/ -f1):$VLLM_PORT/v1/models"
exit 0
