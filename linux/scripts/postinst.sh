#!/bin/sh

trap 'exit' ERR

if [ -x /sbin/initctl ] && /sbin/initctl version | /bin/grep -q upstart; then
  /usr/sbin/service epcontrol start 2>/dev/null || true
elif [ -x /bin/systemctl ]; then
  /bin/systemctl start epcontrol
elif [-x /etc/init.d/epcontrol ]; then
  invoke-rc.d epcontrol start || exit $?
fi

exit 0
