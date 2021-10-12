import struct
import binascii
from Cryptodome.Cipher import AES

#pycryptodome

def parse_value(hexvalue):
	vlength = len(hexvalue)
	# print("vlength:", vlength, "hexvalue", hexvalue.hex(), "typecode", typecode)
	if vlength == 3:
		temp = hexvalue[0]/2 - 40
		humi = hexvalue[1]/2
		batt = hexvalue[2] & 0x7F
		trg =  hexvalue[2] >> 7
		#print("Temperature:", temp, "Humidity:", humi, "Battery:", batt, "Trg:", trg)
		return temp, humi, batt
	if vlength == 6:
		(temp, humi, batt, trg) = struct.unpack("<hHBB", hexvalue)
		#print("Temperature:", temp/100, "Humidity:", humi/100, "Battery:", batt, "Trg:", trg)
		return temp/100, humi/100, batt
	#print("MsgLength:", vlength, "HexValue:", hexvalue.hex())
	return None

def decrypt_payload(payload, key, nonce, mac):
	token = payload[-4:] # mic
	cipherpayload = payload[:-4] # EncodeData
	#print("Nonce: %s" % nonce.hex())
	#print("CryptData: %s" % cipherpayload.hex(), "Mic: %s" % token.hex())
	cipher = AES.new(key, AES.MODE_CCM, nonce=nonce, mac_len=4)
	cipher.update(b"\x11")
	data = None
	try:
		data = cipher.decrypt_and_verify(cipherpayload, token)		
	except ValueError as error:
		mac=mac.hex()
		macReversed=""
		for x in range(-1,-len(mac),-2):
			macReversed += mac[x-1] + mac[x] + ":"
		macReversed = macReversed.upper()[:-1]
		print("ERROR: Decryption failed with sensor MAC (probably wrong key provided):", macReversed)
		return None
	#print("DecryptData:", data.hex())
	#print()
	# if parse_value(data) != None:
	# 	return 1
	# #print('??')
	# return None
	return parse_value(data)

def decrypt_aes_ccm(key, mac, data):
	#print("MAC:", mac.hex(), "Binkey:", key.hex())
	#print()
	adslength = len(data)
	if adslength > 8 and data[0] <= adslength and data[0] > 7 and data[1] == 0x16 and data[2] == 0x1a and data[3] == 0x18:
		pkt = data[:data[0]+1]
		# nonce: mac[6] + head[4] + cnt[1]
		nonce = b"".join([mac, pkt[:5]])
		return decrypt_payload(pkt[5:], key, nonce, mac)
	else:
		print("Error: format packet!")
	return None
