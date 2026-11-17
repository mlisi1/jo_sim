#!/usr/bin/env bash
# Runs inside the recording terminal: "types" each command of a demo, then runs it.
#   demo_term.sh DOMAIN PARTITION 'cmd 1' 'cmd 2' ...
# A command starting with "./jo " runs in the docs domain and partition; "sleep N" pauses silently.
cd "$(dirname "$0")/../../.."
domain=$1 partition=$2; shift 2
PS="\e[1;36m$\e[0m "
type_out() { local s=$1 i; for ((i = 0; i < ${#s}; i++)); do printf '%s' "${s:i:1}"; sleep 0.045; done; }
sleep 4  # the recording starts after the windows are placed
for cmd in "$@"; do
  case "$cmd" in
    sleep\ *) $cmd; continue ;;
  esac
  printf "$PS"; type_out "$cmd"; sleep 0.4; echo
  if [[ $cmd == ./jo\ * ]]; then
    ./jo --domain "$domain" --partition "$partition" ${cmd#./jo }
  else
    bash -c "$cmd"
  fi
  sleep 1.2
done
printf "$PS"
sleep 3
