# PlatformIO project: automatic harvest EE

This project builds the separate sketch at
`../pull_ee_auto_harvest/pull_ee_auto_harvest.ino`; it does not copy or alter
the existing manual teleoperation sketch.

Open this directory in VS Code with PlatformIO IDE. The environment is
`pull_ee_auto_harvest`, using the Raspberry Pi Pico 2 W (`rpipico2w`) and the
Earle Philhower Arduino-Pico core.

To upload on Linux, use `./upload_auto_harvest.sh`. It selects the board by USB
serial number `A437E4B324D4447A`, refuses ambiguous matches and refuses to
upload while another process owns the serial device.
