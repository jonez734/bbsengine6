# systemd drop-ins (reference copies)

These are the intended contents of systemd drop-in files for the host. They are not loaded from
this repo. Copy each file to the same relative path under `/etc/systemd/system/` as root:

    sudo mkdir -p /etc/systemd/system/zoid6.service.d
    sudo cp systemd/zoid6.service.d/utmp.conf /etc/systemd/system/zoid6.service.d/utmp.conf
    sudo systemctl daemon-reload
    sudo systemctl restart zoid6

`utmp.conf` adds the `utmp` group to the zoid6 service, so the process can read `/run/utmp` for the
member's connection address. The installed unit and its `ExecStart` are unchanged. See the zoid6
install guide (handbook/INSTALL.md, section 2) for verification.
