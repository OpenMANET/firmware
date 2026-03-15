#!/bin/sh
#/etc/init.d/network stop

ssid=$(uci get system.@system[0].hostname)

ula_prefix=$(uci get network.globals.ula_prefix)
cp /etc/config/network.bak /etc/config/network
cp /etc/config/wireless.bak /etc/config/wireless
sync

uci set dhcp.lan.ignore='0'
uci commit dhcp

uci set luci.main.homepage='admin/morse/landing'
uci commit luci

uci set network.globals.ula_prefix=$globals.ula_prefix
uci commit network
#uci set network.lan.proto='static'
#uci set network.lan.ipaddr='10.42.0.1'
#uci set network.lan.netmask='255.255.255.0'
#uci delete network.@device[0].ports
#uci delete network.@device[1].ports
#uci commit network
#uci add_list network.@device[0].ports='eth0.1'
#uci commit network


uci set wireless.default_radio0.disabled='0'
uci set wireless.default_radio0.network='lan'
uci set wireless.default_radio0.mode='ap'
uci set wireless.default_radio0.ssid=$ssid
uci set wireless.default_radio0.encryption='psk2'
uci set wireless.default_radio0.key='heltec.org'

uci set wireless.default_radio1.ssid=$ssid
uci set system.@system[0].config='1'
uci commit system

res=$(cat /tmp/sysinfo/board_name|grep "HT-HD01-V2")
if [ "$res" != "" ]
then
	uci set wireless.radio1.bcf='bcf_HD01_v2.bin'
fi

uci commit wireless
#/etc/init.d/network stop
#/morse/scripts/chipreset.sh
sleep 1
/etc/init.d/dnsmasq restart
/etc/init.d/network restart
#/etc/init.d/network reload

