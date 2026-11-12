# PlatformIO project: automatic harvest EE

This project builds the separate sketch at
`../pull_ee_auto_harvest/pull_ee_auto_harvest_limit.ino` and `rail_homing.h`.
The original four-DC and manual teleoperation sketches are retained separately.

Confirmed 2026-11 hardware: roll DC GP10/11 + ADC26; rail DC GP12/13
(positive retract) + encoder GP8/9; hook continuous servo GP17 + FB ADC28;
NC retract limit GP19. The old four-DC firmware conflicts with this servo pin.

Boot is stopped (servo 1500us). Automatic homing starts only on a
`HOME_ENC4` host request, debounces the NC switch locally and then zeros
the encoder. It has timeout, travel, encoder-progress and host-watchdog gates.
An initially open switch must close during bounded release and reopen on
retraction. `ZERO_ENC4` cannot bypass this procedure.

See `src/end_effector_pkg/README_auto_harvest_ja.md` in the workspace for ROS
startup, homing configuration and the required hook feedback calibration.

Open this directory in VS Code with PlatformIO IDE. The environment is
`pull_ee_auto_harvest`, using the Raspberry Pi Pico 2 W (`rpipico2w`) and the
Earle Philhower Arduino-Pico core.

To upload on Linux, use `./upload_auto_harvest.sh`. It selects the board by USB
serial number `A437E4B324D4447A`, refuses ambiguous matches and refuses to
upload while another process owns the serial device.
