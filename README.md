# IDM heat pump

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

_Component to integrate with [IDM heat pumps][idm_heatpump]._

> **Note**:
> Your heat pump needs to have the Navigator 2.0 control unit.
> Other versions of the control unit may not work correctly.

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show on/off-type info from the heat pump.
`sensor` | Show other info from the heat pump.

## Installation

1. Install [HACS](https://hacs.xyz/) and complete its setup.
2. Open HACS and select "Integrations".
3. Add `kodebach/hacs-idm-heatpump` with category "Integration" as a [Custom Repository](https://hacs.xyz/docs/faq/custom_repositories/).
4. Select "IDM heat pump" from the list and click "Download".

## Configuration of the heat pump

The integration communicates with the heat pump via Modbus TCP.
Before Home Assistant can connect to the heat pump you need to make sure "Modbus TCP" is enabled on the heat pump.

> **Warning**: If "Modbus TCP" is not enabled, the integration will fail to connect, even if the web UI of the heat pump is reachable via it given IP or hostname.

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[idm_heatpump]: https://github.com/kodebach/hacs-idm-heatpump
[commits-shield]: https://img.shields.io/github/commit-activity/y/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[commits]: https://github.com/kodebach/hacs-idm-heatpump/commits/master
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Joakim%20Sørensen%20%40ludeeus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[releases]: https://github.com/kodebach/hacs-idm-heatpump/releases
