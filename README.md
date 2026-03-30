# ebusd-ochsner
This Repo contains a documentation of my personal setup to gain access via eBUS with ebusd to my Ochsner Heatpump Air 11 C11A with OCHSNER ÖKO-MASTER PU300 as buffer for the heating and PU800 for hotwater. 
For some general information, please refer to the Wiki from [cybersmart-eu](https://github.com/cybersmart-eu) [Wiki](https://github.com/cybersmart-eu/ebusd-ochsner/wiki/).

# [Ochsner Air 11 C 11 A](https://www.ochsner.com/de-de/ochsner-produkte/air-11-c11a/)
The (on/off) air source heat pump (equipped with an embedded auxiliary heater) has been installed in September 2021 with an Unifresh 500 buffer/boiler (fresh-water station). To control the heat pump, Ochsner is using controllers from [TEM Group](https://www.tem.ch/), thus there is a lot of documentation available as many other vendors also implement TEM controllers in their heat pumps. Many different heat pump models from Ochsner have the same eBUS components embedded and share the same eBUS addresses for many different values and parameters.

## [Ochsner OTE 3](https://www.ochsner.com/fileadmin/downloads/OP/RA_OTE_3+4_EK_DE06.pdf)
The OTE 3/4 ist the User Interface to control the heat pump and internally communicates via eBUS with the Control Unit and other eBUS capable devices. Unfortunately, Ochsner does not provide any interface with API by default allowing remote access and remote control of the heat pump. To access the heat pump from a Home Automation System a gateway is required.
With the help of an ebus Gateway and some re-engineering it is possible to decode the messages on the eBUS and make them "human and machine readable", allowing the eBUS of the Ochsner heat pumps to interface with TCP/IP networks and make them remote controllable.

### Check your Ochsner Hardware and Software Version
Before someone is using my configuration files, I recommend to check the main controller ID, Hardware and Software of your main controller either on the heat pump itself (needs to be opened for that to check the label inside) or with an `ebusd info` command. The main controller is listes with **address 15**, in my case with **ID 24849, SW-Version 0605 and Hardware revision 0102**. This is also part of the naming convention of the configuration file as per [John's instructions](https://github.com/john30/ebusd-configuration), so that ebusd can automatically pick the best fitting configuration file in case several configuration files are found.
For my heatpump the ebus pins are 41 and 42 where the room control panel is connected and now also my ebus connector.

![IMG_9585](https://github.com/SmartLessing/ebusd-ochsner/assets/172171816/72860a4a-0de7-4e8d-8d0b-85d5bba65ab8)

### ebusctl info ###
```
version: ebusd 23.3.23.3
update check: OK
device: ebus-air11:9999, TCP, enhanced, firmware 1.1[460f].1[460f]
access: *
signal: acquired
symbol rate: 39
max symbol rate: 242
min arbitration micros: 0
max arbitration micros: 54
min symbol latency: 0
max symbol latency: 76
scan: finished
reconnects: 0
masters: 5
messages: 102
conditional: 0
poll: 73
update: 0
address 01: master #6
address 03: master #11
address 06: slave #6, scanned "MF=TEM;ID=25440;SW=0113;HW=0000"
address 08: slave #11, scanned "MF=TEM;ID=WE_1 ;SW=3632;HW=3030"
address 10: master #2
address 13: master #12
address 15: slave #2, scanned "MF=TEM;ID=24849;SW=0605;HW=0102", loaded "tem/15.24849.HW0102.SW0605.csv"
address 18: slave #12, scanned "MF=TEM;ID=WE_2 ;SW=3632;HW=3030"
address 31: master #8, ebusd
address 36: slave #8, ebusd
address 91: slave, scanned "MF=TEM;ID=26984;SW=0120;HW=0100"
```

## The Gateway - ebusd and adapters
Luckily, a software developer with nickname [john30](https://github.com/john30) developed an "ebus deamon", acting as an eBUS gateway, and provides his Open-Source software [ebusd](https://github.com/john30/ebusd) free of charge via github. A hardware adapter as serial interface is required, to physically connect the eBUS with computer hardware. John, the author of ebusd also provides [hardware adapters ](https://adapter.ebusd.eu/) for this purpose, but also other available 3rd party adapters shall do the job.

# The Magic - how to decode the data on the eBUS
Unfortunately, there is no vendor documentation available from Ochsner or TEM Group related to the specific eBUS protocol they use. Every vendor can integrate and use eBUS as they want, so decoding the data means re-enignineering is required. John also maintains a [ebusd-config](https://github.com/john30/ebusd-configuration) repository where he collects and provides ready-to-use config files for different eBUS devices, mainly (latest config files) for Vaillant devices, but also some older Ochsner configuration files can be found there. 
An Ochsner related Discussion on Johns github motivated me to fork the work of [Uwe]([https://github.com/cybersmart-eu](https://github.com/cybersmart-eu/ebusd-ochsner)) to refine it in a way so that Home Assistant integration works out of the box with a slightly modfied configuration.
Please also check out the github repos of [Uwe](https://github.com/cybersmart-eu), [Lori](https://github.com/Lorilatschki) and [Wolfgang](https://github.com/wiedwo) as we are sitting in the same boat together :-)

## ebusd - most important commands

### ebusd grab result all decode
Dump ebus data

```bash
ebusctl grab result all decode > /home/auser/decode.all.txt
```

File content of decode.all.txt
```
...
31150621047d800002 / 0a35810000ff0000000000 = 4: 24849 heatpump_status_string
 BCD   35=35, 81=81, 00=0, 00=0, ff=-, 00=0, 00=0, 00=0, 00=0, 00=0
 BCD:2 3581=8135, 8100=81, 0000=0, 00ff=-, ff00=-, 0000=0, 0000=0, 0000=0, 0000=0
 BCD:3 358100=8135, 810000=81, 0000ff=-, 00ff00=-, ff0000=-, 000000=0, 000000=0, 000000=0
 BCD:4 35810000=8135, 810000ff=-, 0000ff00=-, 00ff0000=-, ff000000=-, 00000000=0, 00000000=0
 BDY   00=Mon, 00=Mon, 00=Mon, 00=Mon, 00=Mon, 00=Mon, 00=Mon
 BTI   0000ff="-:00:00", 00ff00="00:-:00", ff0000="00:00:-", 000000="00:00:00", 000000="00:00:00", 000000="00:00:00"
 BTM   0000="00:00", 00ff="-:00", ff00="00:-", 0000="00:00", 0000="00:00", 0000="00:00", 0000="00:00"
 D1B   35=53, 81=-127, 00=0, 00=0, ff=-1, 00=0, 00=0, 00=0, 00=0, 00=0
 D1C   35=26.5, 81=64.5, 00=0.0, 00=0.0, ff=-, 00=0.0, 00=0.0, 00=0.0, 00=0.0, 00=0.0
 D2B   3581=-126.793, 8100=0.504, 0000=0.000, 00ff=-1.000, ff00=0.996, 0000=0.000, 0000=0.000, 0000=0.000, 0000=0.000
 D2C   3581=-2028.69, 8100=8.06, 0000=0.00, 00ff=-16.00, ff00=15.94, 0000=0.00, 0000=0.00, 0000=0.00, 0000=0.00
 DAY   3581="25.07.1990", 8100="10.05.1900", 0000="03.01.1900", 00ff="24.09.2078", ff00="-.13.09.1900", 0000="03.01.1900", 0000="03.01.1900", 0000="03.01.1900", 0000="03.01.1900"
 DTM   35810000="23.01.2009 23:17", 810000ff="13.05.2092462 18:09", 0000ff00="10.10.2040 08:00", 00ff0000="15.02.2009 08:00", ff000000="01.01.2009 04:15", 00000000="01.01.2009 00:00", 00000000="01.01.2009 00:00"
 EXP   35810000=4.63507e-41, 810000ff=-1.70144e+38, 0000ff00=2.34181e-38, 00ff0000=9.14768e-41, ff000000=3.57331e-43, 00000000=0.0, 00000000=0.0
 EXR   35810000=9.61125e-07, 810000ff=-2.35106e-38, 0000ff00=9.14768e-41, 00ff0000=2.34181e-38, ff000000=-1.70141e+38, 00000000=0.0, 00000000=0.0
 FLR   3581=13.697, 8100=-32.512, 0000=0.000, 00ff=0.255, ff00=-0.256, 0000=0.000, 0000=0.000, 0000=0.000, 0000=0.000
 FLT   3581=-32.459, 8100=0.129, 0000=0.000, 00ff=-0.256, ff00=0.255, 0000=0.000, 0000=0.000, 0000=0.000, 0000=0.000
 HCD   00000000=0, 00000000=0
 HCD:1 35=53, 00=0, 00=0, 00=0, 00=0, 00=0, 00=0, 00=0
 HCD:2 0000=0, 0000=0, 0000=0, 0000=0, 0000=0
 HCD:3 000000=0, 000000=0, 000000=0
 HDY   00=Tue, 00=Tue, 00=Tue, 00=Tue, 00=Tue, 00=Tue, 00=Tue
 HEX:10 35810000ff0000000000="35 81 00 00 ff 00 00 00 00 00"
 HTI   0000ff="00:00:-", 00ff00="00:-:00", ff0000="-:00:00", 000000="00:00:00", 000000="00:00:00", 000000="00:00:00"
 HTM   0000="00:00", 00ff="00:-", ff00="-:00", 0000="00:00", 0000="00:00", 0000="00:00", 0000="00:00"
 MIN   8100="02:09", 0000="00:00", 00ff=":-", ff00="-04:15", 0000="00:00", 0000="00:00", 0000="00:00", 0000="00:00"
 NTS:10 35810000ff0000000000="5?"
 PIN   3581=3581, 8100=8100, 0000=0000, 00ff=-, ff00=-, 0000=0000, 0000=0000, 0000=0000, 0000=0000
 S3N   358100=33077, 810000=129, 0000ff=-65536, 00ff00=65280, ff0000=255, 000000=0, 000000=0, 000000=0
 S3R   358100=3506432, 810000=-8323072, 0000ff=255, 00ff00=65280, ff0000=-65536, 000000=0, 000000=0, 000000=0
 SCH   35=53, 81=-127, 00=0, 00=0, ff=-1, 00=0, 00=0, 00=0, 00=0, 00=0
 SIN   3581=-32459, 8100=129, 0000=0, 00ff=-256, ff00=255, 0000=0, 0000=0, 0000=0, 0000=0
 SIR   3581=13697, 8100=-32512, 0000=0, 00ff=255, ff00=-256, 0000=0, 0000=0, 0000=0, 0000=0
 SLG   35810000=33077, 810000ff=-16777087, 0000ff00=16711680, 00ff0000=65280, ff000000=255, 00000000=0, 00000000=0
 SLR   35810000=897646592, 810000ff=-2130706177, 0000ff00=65280, 00ff0000=16711680, ff000000=-16777216, 00000000=0, 00000000=0
 STR:10 35810000ff0000000000="5?"
 TEM_P 3581=02-053, 8100=01-001, 0000=00-000, 00ff=30-000, ff00=01-127, 0000=00-000, 0000=00-000, 0000=00-000, 0000=00-000
 TTM   35="08:50", 81="21:30", 00="00:00", 00="00:00", 00="00:00", 00="00:00", 00="00:00", 00="00:00", 00="00:00"
 U3N   358100=33077, 810000=129, 0000ff=16711680, 00ff00=65280, ff0000=255, 000000=0, 000000=0, 000000=0
 U3R   358100=3506432, 810000=8454144, 0000ff=255, 00ff00=65280, ff0000=16711680, 000000=0, 000000=0, 000000=0
 UCH   35=53, 81=129, 00=0, 00=0, ff=-, 00=0, 00=0, 00=0, 00=0, 00=0
 UIN   3581=33077, 8100=129, 0000=0, 00ff=65280, ff00=255, 0000=0, 0000=0, 0000=0, 0000=0
 UIR   3581=13697, 8100=33024, 0000=0, 00ff=255, ff00=65280, 0000=0, 0000=0, 0000=0, 0000=0
 ULG   35810000=33077, 810000ff=4278190209, 0000ff00=16711680, 00ff0000=65280, ff000000=255, 00000000=0, 00000000=0
 ULR   35810000=897646592, 810000ff=2164261119, 0000ff00=65280, 00ff0000=16711680, ff000000=4278190080, 00000000=0, 00000000=0
 VTI   000000="00:00:00", 000000="00:00:00", 000000="00:00:00"
 VTM   0000="00:00", 00ff="-:00", ff00="00:-", 0000="00:00", 0000="00:00", 0000="00:00", 0000="00:00"
...
```

### ebusctl listen
```
listen started

24849 heating/temp.outside = 0;0;0d;2;50.0;-50.0;23.9
24849 heatpump/temp.tqe = 71;0;0d;2;100.0;0.0;22.7
24849 heatpump/temp.tqa = 70;0;0d;2;100.0;0.0;21.5
```

### eusctl scan result
```
ebusctl scan result
06;TEM;25440;0113;0000
08;TEM;WE_1 ;3632;3030
15;TEM;24849;0605;0102
18;TEM;WE_2 ;3632;3030
91;TEM;26984;0120;0100
```

### ebusctl read
```
ebusctl read heatpump_status_string
53;1;00;0;25.5;0.0;Standby
```

### ebusctl write
```
ebusctl write -c 24849 heatpump_mode_set_write 0
done
```

## ebusd - configuration files

```
Setting up ebusd (23.3) ...
Instructions:
1. Edit /etc/default/ebusd if necessary
   (especially if your device is not /dev/ttyUSB0)
2. Start the daemon with 'systemctl start ebusd'
3. Check the log file /var/log/ebusd.log
4. Make the daemon autostart with 'systemctl enable ebusd'
```

```
/etc/default/ebusd
EBUSD_OPTS="--scanconfig --configpath=/etc/ebusd/ -d mdns:543204295c04 --httpport=8889 --htmlpath=/va$ --mqtthost=192.168.1.32 --mqttport=1883 --mqttint=/etc/ebusd/mqtt-hassio.cfg --mqttjson"
```

# My Hardware

## Lenovo ThinkCentre M70q
I migrated from a Raspberry Pi 5 to a Proxmox based home server using a refurbished Lenovo ThinkCentre M70q 11DT - Mini - Core i3 10100T / 3 GHz. I installed 32 GB of Ram and a 512 SSD to host Linux Containers (LXC) and virtual machines (VM). I run Proxmox and have two Linux Containers in place to host software for the heatpump: one for Mosquitto and one for ebusd.
HomneAssistant is running in a virtual Machine.

![240a744dabb97b39a3b42f2cd519bcf4_3](https://github.com/user-attachments/assets/a1400a5c-dd09-4e9f-82f0-91213ea24677)

### Useful Links
https://www.proxmox.com/en/
https://forums.servethehome.com/index.php?threads/lenovo-thinkcentre-thinkstation-tiny-project-tinyminimicro-reference-thread.34925/
https://community-scripts.github.io/ProxmoxVE/scripts

## eBUS Adapter Shield C6
eBUS Adapter Shield C6, which can be used to communicate with an eBUS enabled heating, ventilation or solar system.
https://adapter.ebusd.eu

# Some (additional) useful Software

## MQTT - Mosquitto
Eclipse Mosquitto is an open source (EPL/EDL licensed) message broker that implements the MQTT protocol versions 5.0, 3.1.1 and 3.1. Mosquitto is lightweight and is suitable for use on all devices from low power single board computers to full servers.

The MQTT protocol provides a lightweight method of carrying out messaging using a publish/subscribe model. This makes it suitable for Internet of Things messaging such as with low power sensors or mobile devices such as phones, embedded computers or microcontrollers.

https://mosquitto.org

## MQTT-Explorer
MQTT Explorer is a comprehensive MQTT client that provides a structured overview of your MQTT topics and makes working with devices/services on your broker dead-simple.
<img width="1136" alt="Bildschirmfoto 2024-07-05 um 19 11 24" src="https://github.com/SmartLessing/ebusd-ochsner/assets/172171816/7b33ed10-cfac-4053-9dae-8e1b2915060a">


# Home Assistant
Awaken your home
Open source home automation that puts local control and privacy first. Powered by a worldwide community of tinkerers and DIY enthusiasts. Perfect to run on a Raspberry Pi or a local server.

https://www.home-assistant.io

This is my dashboard for my heatpump:
<img width="1269" alt="Bildschirmfoto 2025-04-13 um 09 28 07" src="https://github.com/user-attachments/assets/0a7b8691-9ac5-4bb0-8135-a878c21fda71" />

## YAML Code for setting date and time in the heatpumo via MQTT

Prerequisites: write messages are activated in mqtt-hassio.cfg: `filter-direction = r|u|^w`

Hint: A slash `/` in the topic string will not work, as ebus does not support it: https://github.com/john30/ebusd/issues/1302

```yaml
service: mqtt.publish
metadata: {}
data:
  topic: ebusd/24849/service_time_set_write/set
  payload: "{{ now().strftime('%H:%M') }}"
```
