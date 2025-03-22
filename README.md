> [!IMPORTANT]
> This integration is not affiliated with iDM Energiesysteme GmbH and is provided as-is and without warranty.

# IDM heat pump

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

_Component to integrate with [IDM heat pumps][https://www.idm-energie.at/]._

> [!NOTE]
> Your heat pump needs to have the Navigator 2.0 control unit.
> Other versions of the control unit may not work correctly.

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show on/off-type info from the heat pump.
`sensor` | Show other info from the heat pump.

## Installation

### Configuration of the heat pump

The integration communicates with the heat pump via Modbus TCP.
Before Home Assistant can connect to the heat pump you need to make sure **Modbus TCP** is enabled on the heat pump.

> [!IMPORTANT]
> If **Modbus TCP** is not enabled, the integration will fail to connect, even if the web UI of the heat pump is reachable via it given IP or hostname.

### Install HACS Repository

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kodebach&repository=hacs-idm-heatpump&category=integration)

1. Install [HACS](https://hacs.xyz/) and complete its setup.
2. Open HACS and select "Integrations".
3. Add `kodebach/hacs-idm-heatpump` with category "Integration" as a [Custom Repository](https://hacs.xyz/docs/faq/custom_repositories/).
4. Select "IDM heat pump" from the list and click "Download".

### Set up integration

[![Add integration to Home Assistant!](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=idm_heatpump)

The integration now appears like any other Home Assistant integration.
To set it up, follow these steps:

1. In the HA UI go to "Settings" -> "Devices & Services", click "+ Add Integration" in the bottom right corner, and search for "IDM heat pump".
2. Make sure the heat pump is configured correctly (see above), then fill out the necessary details in the setup form.

### Further configuration

[![Configure my setup!](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=idm_heatpump)

For further configuration you can click "Configure" on the settings page for the integration.

## Additional notes for sensor data

- **Status Ladepumpe**:
  This value is reported as a percentage in the IDM interface, but has a range of -1 to 100, with -1 meaning "pump is off", 0 meaning "pump running at minimum speed" and 100 meaning "pump running at maximum speed".
  To avoid confusion about the what -1% means and how values between 0 and 100 should be interpreted, this integration reports the value without unit and leaves interpretation to the user.
  You may want to add extra sensor to your `configuration.yaml` file to get more sensible data:

  ```yaml
  binary_sensor:
    - platform: threshold # use a threshold sensor to check whether charge pump is active
      name: "Ladepumpe aktiv"
      entity_id: sensor.heatpump_status_ladepumpe # replace with your entity id
      upper: 0
  ```

  > **Note**:
  > It may be that your heat pump does not have variable speed charge pumps, in which case you probably would only see the values -1 and 100.
  > The binary sensor above will still work for that case.
  > For the other cases it is harder, because other than -1 meaning "power off" and 0-100 "power on at some speed", IDM documentation doesn't say how values should be interpreted.
  > However, we can make some guesses for the two common types of variable speed pumps:
  > - _0-10 V controlled pumps_:
  >   The 0-100 value probably maps directly to the 0-10 V signal, either `0->0,x->x/10,100->10` or `0->10,x->10-x/10,100->0`, depending on whether 10 V or 0 V is for maximum speed.
  > - _PWM controlled pumps_:
  >   The 0-100 value probably indicates the PWM duty cycle as a percentage.
  >   Again, it could be 0 or 100 that mean PWM always active, depending on what the pump interprets as "run at maximum speed".
  > These conversions could be done with a template sensor in `configuration.yaml`.
- **Status Sole/Zwischenkreispumpe** and **Status Wärmequellen/Grundwasserpumpe**:
  I assume these two work the same as "Status Ladepumpe".
  However, the documentation from IDM doesn't really say, and my setup doesn't use these, so I cannot verify it myself.
- **Umschaltventil ... X/Y**:
  All the "Umschaltventil ... X/Y" sensors are implemented such that the value `0` from the heat pump is interpreted as X and `1` is interpreted as Y.
  The special value `0xFFFF`/`-1` is interpreted as "not available", any other value (e.g. `-1`) is interpreted as "unknown".
  This is a bit of a guess, since the documentation from IDM does not give any information for these sensors (other than that they exist), but this interpretation works correctly for my setup.

## Contributions are welcome

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[idm_heatpump]: https://github.com/kodebach/hacs-idm-heatpump
[commits-shield]: https://img.shields.io/github/commit-activity/y/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[commits]: https://github.com/kodebach/hacs-idm-heatpump/commits/master
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/kodebach/hacs-idm-heatpump.svg?style=for-the-badge
[releases]: https://github.com/kodebach/hacs-idm-heatpump/releases
