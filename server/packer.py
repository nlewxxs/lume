#!/usr/bin/env python3
"""
Post processing to be done server-side for sensor data being received. This
includes calculating means, variances and energies. There is also an option to
do an FFT, as this was required for choosing the appropriate corner frequency
for the LPFs on the controller side. 
"""

from typing import List, Dict
import struct

def pack_binary(data : List[float]) -> bytes:
    """Pack the filtered and post-processed sensor data into bytes""" 

    # First pack the values of flex0, flex1 and flex2 into a boolean (these
    # are passed as 0.0, or 1.0 into the function)
    flex_byte = 0x0
    flex_byte |= (0b10000000 if data[:-3] == 1.0 else 0b0)
    flex_byte |= (0b01000000 if data[:-2] == 1.0 else 0b0)
    flex_byte |= (0b00100000 if data[:-1] == 1.0 else 0b0)

    data = data[:-3]
    data.append(flex_byte)

    packed_data = struct.pack('<26fB', *data)
    return packed_data

def unpack_binary(data : bytes) -> Dict:
    """
    Unpack the data from bytes into a dictionary to be stored in postgres.
    This function is not responsible for converting to json, though this can
    easily be done using json.dumps() later on
    """
    
    unpacked = struct.unpack('<26fB', data)

    result = {
            "pitch":    unpacked[0], 
            "roll" :    unpacked[1], 
            "yaw" :     unpacked[2],
            "d_pitch" : unpacked[3],
            "d_roll" :  unpacked[4],
            "d_yaw" :   unpacked[5],
            "acc_x" :   unpacked[6],
            "acc_y" :   unpacked[7],
            "acc_z" :   unpacked[8],
            "acc_x_mean" :  unpacked[9],
            "acc_y_mean" :  unpacked[10],
            "acc_z_mean" :  unpacked[11],
            "acc_x_var" :   unpacked[12],
            "acc_y_var" :   unpacked[13],
            "acc_z_var" :   unpacked[14],
            "gy_x" :    unpacked[15],
            "gy_y" :    unpacked[16],
            "gy_z" :    unpacked[17],
            "gy_x_mean" :   unpacked[18],
            "gy_y_mean" :   unpacked[19],
            "gy_z_mean" :   unpacked[20],
            "gy_x_var" :    unpacked[21],
            "gy_y_var" :    unpacked[22],
            "gy_z_var" :    unpacked[23],
            "acc_energy" :  unpacked[24],
            "gy_energy" :   unpacked[25],
            "flex0" :   float(unpacked[26] & 0b10000000 != 0),
            "flex1" :   float(unpacked[26] & 0b01000000 != 0),
            "flex2" :   float(unpacked[26] & 0b00100000 != 0)
            }

    return result

