# IDM heat pump

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

_Component to integrate with [IDM heat pumps][idm_heatpump]._

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show something `True` or `False`.
`sensor` | Show info about the heat pump.
## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `idm_heatpump`.
4. Download _all_ the files from the `custom_components/idm_heatpump/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "IDM heat pump"

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/idm_heatpump/translations/en.json
custom_components/idm_heatpump/__init__.py
custom_components/idm_heatpump/api.py
custom_components/idm_heatpump/binary_sensor.py
custom_components/idm_heatpump/config_flow.py
custom_components/idm_heatpump/const.py
custom_components/idm_heatpump/manifest.json
custom_components/idm_heatpump/sensor.py
```

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[idm_heatpump]: https://github.com/kodebach/hacs-idm-heatpump
[commits-shield]: https://img.shields.io/github/commit-activity/y/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[commits]: https://github.com/kodebach/hacs-idm-heatpump/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Joakim%20Sørensen%20%40ludeeus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[releases]: https://github.com/kodebach/hacs-idm-heatpump/releases
