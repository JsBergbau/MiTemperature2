#!/bin/bash

set -e 

##################################################### Config

# Default values if no config exists
ZBX_ADDRESS=localhost
ZBX_PORT=10051

SCRIPT_DIR=$(dirname ${0})
if [[ -f ${SCRIPT_DIR}/sendToZabbix.conf ]]; then
	. ${SCRIPT_DIR}/sendToZabbix.conf
fi

##################################################### TLS

TLS_PARAMS=''
if [[ "${TLS_CONNECT}" == "psk" ]]; then
	if [[ ! -f ${TLS_PSK_FILE} ]]; then
		if [[ -f ${SCRIPT_DIR}/${TLS_PSK_FILE} ]]; then
			TLS_PSK_FILE=${SCRIPT_DIR}/${TLS_PSK_FILE}
		else
			echo "File not found: ${TLS_PSK_FILE}"
			exit 1
		fi
	fi
	TLS_PARAMS=(--tls-connect psk --tls-psk-identity ${TLS_PSK_IDENTITY} --tls-psk-file ${TLS_PSK_FILE})
fi

##################################################### Data preparation

# removes ':' from sensor name in caseof MAC address is used
ZBX_HOST=${2//:/}

# value mapping
TEMPERATURE=${3}
HUMIDITY=${4}
BATTERY_VOLTAGE=${5}
BATTERY_LEVEL=${6}

##################################################### Transfer

echo "${ZBX_HOST} MiTemperature2.battery_level ${BATTERY_LEVEL}
${ZBX_HOST} MiTemperature2.battery_voltage ${BATTERY_VOLTAGE}
${ZBX_HOST} MiTemperature2.humidity ${HUMIDITY}
${ZBX_HOST} MiTemperature2.temperature ${TEMPERATURE}" | zabbix_sender -z ${ZBX_ADDRESS} -p ${ZBX_PORT} -s - -i - ${TLS_PARAMS[@]}

