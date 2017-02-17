#!/bin/sh

trap 'exit' ERR

if [ -x /sbin/initctl ] && /sbin/initctl version | /bin/grep -q upstart; then
  /usr/sbin/service epcontrol stop 2>/dev/null || true
  /usr/sbin/service epcontrol start 2>/dev/null
elif [ -x /bin/systemctl ]; then
  /bin/systemctl enable sighstone
  /bin/systemctl restart epcontrol
elif [-x /etc/init.d/epcontrol ]; then
  update-rc.d epcontrol defaults > /dev/null
  invoke-rc.d epcontrol start || exit $?
fi

exit 0
