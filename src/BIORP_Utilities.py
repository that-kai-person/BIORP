import pyaudio
import wave
import numpy.fft as fft
import numpy as np
import tkinter as tk
import ctypes

"""
	BIORP | Binary Information Over Radio Protocol
	
	Written by Kai Dekel
"""

"""
	BIORP PROTOCOL DOCUMENTATION

	SYN | MOD | LEN | DTYPE | CHECKSUM | DATA | END

	SYN - Sync message. 20 SYN tokens, mainly to key up the VOX and prepare the other side for transmit.

	MOD - Mode of operation. 2 bit code of either:
		00 - TEST MODE, will transmit a pre-known series of bits.
		01 - HAM MODE, will transmit text info of Callsign, QTH, Local time and QSL info (TX/RX and where to QSL).
				ENCRYPTION IS DISABLED IN THIS MODE
		10 - DATA MODE, will transmit a supported datatype in DATA.
		11 - CUSTOM MODE, no headers are required. For developers and custom usage.

	LEN - Length of message (From start of DTYPE to the end of DATA). 32-bit integer.

	DTYPE - Datatype of DATA, AKA how to read DATA. Supported datatypes:
			Text (Bit data of string), .txt, .jpeg, .exe

	CHECKSUM - 16-bit checksum to know if any data was corrupted.

	DATA - Sent data in bits, max length in bits of 4,294,967,296 bits (~530MB, 32-bit LEN)

	END - End message declaring end of tx. 3 SYN tokens.
	"""

# STANDARD PARAMETERS

STD_FORMAT = pyaudio.paInt16  # Sampling format for RX
STD_CHAN = 1  # 1 for mono, 2 for stereo. UV-K6 does NOT work with stereo.
STD_RATE = 44100  # Sample rate for RX
STD_TX = 1/15  # 100 bit per second (BpSec) TX rate
STD_CHUNK = int(STD_RATE*STD_TX)  # Sampling chunk for RX

frequencies = {"0": 400,
			   "1": 600,
			   "SYN": 500}

def compare_lists(list1, list2):
    set1, set2 = set(list1), set(list2)
    
    only_in_list1 = set1 - set2
    only_in_list2 = set2 - set1
    common_elements = set1 & set2
    differences = only_in_list1 | only_in_list2

    return {
        "only_in_list1": list(only_in_list1),
        "only_in_list2": list(only_in_list2),
        "common_elements": list(common_elements),
        "differences": list(differences)
    }

def bytes_to_bits(input: bytes):  # Convert the bytes received from pyaudio to bits for files
	bit_list = []
	for byte in input:
		# Convert the byte to an 8-bit binary string (e.g., 0b10101001 -> '10101001')
		bits = format(byte, '08b')
		# Add each bit to the bit_list (you can also use a list comprehension here)
		bit_list.extend(bits)

	return bit_list

def bits_to_bytes(bits: list[str]) -> bytes:
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte |= (int(bits[i + j]) << (7 - j))
        result.append(byte)
    return bytes(result)

def rms(input: list):
	return np.sqrt(np.mean(np.square(input)))


def peak_amplitude(input: list):
	return np.max(np.abs(input))


def generate_sine_wave(frequency, duration, rate):
	t = np.linspace(0, duration, int(rate * duration), endpoint=False)
	return np.sin(2 * np.pi * frequency * t)


def calc_checksum(bits: list[str]) -> list[str]:
    # 1. Guard: no junk in your bit‐list
    if any(b not in ('0', '1') for b in bits):
        raise ValueError(f"calc_checksum expected only '0'/'1', got: {bits[:16]}…")

    total = 0
    # 2. Sum 16‐bit chunks
    for i in range(0, len(bits), 16):
        chunk = bits[i:i + 16]
        total += int("".join(chunk), 2)

    # 3. Modulo into 16 bits, then rebuild a list of '0'/'1'
    checksum_value = total % 0x10000
    return list(f"{checksum_value:016b}")


def validate_checksum(checksum_plus_data: list):
	# Separate into data and checksum
	data = checksum_plus_data[:-16]
	checksum_received = checksum_plus_data[-16:]

	# Recalculate checksum
	checksum_calculated = calc_checksum(data)

	corrupted = not (checksum_received == checksum_calculated)

	corrupted_count = 0
	for n in range(0, len(checksum_calculated)):
		if not (checksum_calculated[n] == checksum_received[n]):
			corrupted_count += 1

	return corrupted, corrupted_count


def round_to_freqs(data: list): # +- 20Hz error mrgain for data, with an 80Hz error margain for SYN
    rounded_list = []
    for cell in data:
        if cell > 620 or cell < 380:
            continue
        if 380 <= cell <= 420:
            rounded_list.append(400)
        elif 580 <= cell <= 620:
            rounded_list.append(600)
        elif 421 <= cell <= 579:
            rounded_list.append(500)
    return rounded_list




# ------------------------- RX - RECEIVE -------------------------


def record_audio(record_seconds, chunk=STD_CHUNK, format=STD_FORMAT, channels=STD_CHAN, rate=STD_RATE):
	#  Example function for stream functionality and usage
	p = pyaudio.PyAudio()

	stream = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)

	frames = []

	for i in range(0, int(rate / chunk * record_seconds)):
		data = stream.read(chunk)
		frames.append(data)

	stream.stop_stream()
	stream.close()
	p.terminate()

	return frames


def listen_record(thresh=500, chunk=STD_CHUNK, format=STD_FORMAT, channels=STD_CHAN, rate=STD_RATE):
	# Create a np array buffer to store last 3 secs of audio data
	buffer_size = rate * 3
	buffer = np.zeros(buffer_size, dtype=np.int16)

	# Open a data stream
	p = pyaudio.PyAudio()
	stream = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)

	recording = False
	return_audio = []

	while True:
		# Take in data from stream
		audio_data = np.frombuffer(stream.read(chunk, exception_on_overflow=False), dtype=np.int16)

		# Roll back buffer for new data
		buffer[:] = np.roll(buffer, -chunk)
		buffer[-chunk:] = audio_data

		# See if exists audio activity using rms
		if rms(buffer.tolist()) >= thresh:
			if not recording:
				# New audio activity detected
				print("PICKED UP SOUND")
				recording = True
				return_audio = buffer.copy().tolist()
			
			return_audio.extend(audio_data)
			print("still recording...")

		elif recording and rms(buffer.tolist()) <= thresh:
			# Audio is beneath thresh at end of record
			recording = False
			print("END RECORDING")
			break

	# Close stream
	stream.stop_stream()
	stream.close()
	p.terminate()


	# Clean output in case of mess-ups below thresh
	# Find the first index where where we're over thresh
	start = None
	for i in range(len(return_audio)):
		if abs(return_audio[i]) >= thresh:
			start = i
			break
	
	# Find the last index where we're over thresh
	end = None
	for i in range(len(return_audio) - 1, -1, -1):
		if abs(return_audio[i]) >= thresh:
			end = i
			break

	# If no valid sound is found (AKA error), return an empty list
	if start is None or end is None:
		return []

	return return_audio[start:end + 1]  # Returns a list


def chunk_to_dominant_freq(samples:list, sample_rate=STD_RATE, chunk=STD_CHUNK):
    samples = np.asarray(samples)

    # Generate Hann window using NumPy
    hann_window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(len(samples)) / (len(samples) - 1))
    windowed_samples = samples * hann_window

    # Zero-padding
    if len(samples) < chunk:
        padded = np.zeros(chunk)
        padded[:len(samples)] = windowed_samples
    else:
        padded = windowed_samples[:chunk]

    # FFT using NumPy
    fft_result = np.fft.fft(padded)
    freqs = np.fft.fftfreq(chunk, d=1.0 / sample_rate)

	# Shape waveform for manipulation (Flip all negatives)
    magnitudes = np.abs(fft_result[:chunk // 2])
    positive_freqs = freqs[:chunk // 2]

    threshold = np.max(magnitudes) * 0.1 # Get the thresh of the maximal intensity freq
    valid_indices = np.where(magnitudes > threshold)[0] # Get dominant freq using thresh

    if len(valid_indices) == 0:
        return 0.0

    peak_index = valid_indices[np.argmax(magnitudes[valid_indices])]
    return positive_freqs[peak_index]


def to_dominant_freqs(audio_data: list, read_chunk=STD_CHUNK, rate=STD_RATE):
    """
    Split the raw audio into chunks for reading, run FFT,
    and return one dominant frequency per chunk.
    """
    freqs = []
    for start in range(0, len(audio_data), read_chunk):
        chunk = audio_data[start:start + read_chunk]
        if len(chunk) < read_chunk:
            break
        freqs.append(chunk_to_dominant_freq(chunk, rate))
    return freqs



def find_tx_rate(freqs: list):
	print("WIP")
	return


def freqs_to_bits(freqs: list[float],
                  tx_rate: float = STD_TX,
                  chunk: int = STD_CHUNK,
                  rate: float = STD_RATE) -> list[str]:
	"""
	Turn a time‑series of dominant frequencies into ['0','SYN','1',...] tokens
	for extraction from protocol and translation to data.
	"""
	# REMOVE INVALID SILENT FREQUENCIES
	freqs = [f for f in freqs if f > 0]
	# How many frequency readings per transmitted bit?
	#    (chunk/rate) = seconds per frequency sample
	#    tx_rate    = bits per second
	#    samples_per_bit = freq‑reads per bit
	samples_per_bit = max(1, round((chunk / rate) / tx_rate))

	# Group into non‑overlapping blocks, each representing one bit
	grouped = []
	for i in range(0, len(freqs), samples_per_bit):
		block = freqs[i:i + samples_per_bit]
		if len(block) == samples_per_bit:
			grouped.append(block)

    # For each block, compute its RMS “strength” and snap it to 450/500/550
	tone_avgs = [np.mean(block) for block in grouped]
	snapped = round_to_freqs(tone_avgs)  # yields [450,500,550,...]

	# Map each snapped tone to a bit‑token
	bit_tokens = []
	for f in snapped:
		if f == 400:
			bit_tokens.append('0')
		elif f == 500:
			bit_tokens.append('SYN')
		elif f == 600:
			bit_tokens.append('1')
		else:
			raise ValueError(f"Unexpected tone {f} in freqs_to_bits")

	return bit_tokens

def bit_protocol_to_bytes(bit_data: list, custom_start: int = 0, custom_end : int = 0):
	no_syn = [bit for bit in bit_data if bit != 'SYN']  # Remove 'SYN' tokens

	if len(no_syn) < 2:	raise ValueError("Too few bits to determine mode.")

	mode_bits = no_syn[0:2] # Extract mode bits
	mode = ''.join(mode_bits) # Make into string

	match mode:  # Match for mode
		case '00' | '01':  # Test mode and HAM mode
			len_bits = no_syn[2:18]
			length = int(''.join(len_bits),2)

			checksum = no_syn[18:34]
			data_bits = no_syn[34:34+length]

			corrupted, corrupted_count = validate_checksum(data_bits + checksum)
			if corrupted:
				print("Warning: Checksum mismatch", corrupted_count, " bits wrong). Proceeding anyway for debug.")
			print("DATA BITS:", data_bits)
			print("EXPECTED CHECKSUM:", calc_checksum(data_bits))
			print("RECEIVED CHECKSUM:", checksum)
			return bits_to_bytes(data_bits), mode, None
		
		case '10':  # Data mode
			len_bits = no_syn[2:34]
			length = int(''.join(len_bits),2)

			filetype_bits = no_syn[34:66] # 4 bytes = 32 bits
			filetype = bits_to_bytes(filetype_bits).decode('utf-8', errors='replace').strip('\x00')

			checksum = no_syn[66:82]
			data_bits = no_syn[82:82+length]

			corrupted, corrupted_count = validate_checksum(data_bits + checksum)
			if corrupted:
				print("Warning: Checksum mismatch", corrupted_count, " bits wrong). Proceeding anyway for debug.")

			print("MODE:", mode)
			print("DATA BITS:", data_bits)
			print("EXPECTED CHECKSUM:", calc_checksum(data_bits))
			print("RECEIVED CHECKSUM:", checksum)
			return bits_to_bytes(data_bits), mode, filetype

		case '11':  # Custom mode
			data_bits = no_syn[custom_start:custom_end]
			return bits_to_bytes(data_bits), mode, None	
		
		case _:
			raise Exception("Incorrect mode bits: ", mode)

def handle_rx(chunk=STD_CHUNK, format=STD_FORMAT, channels=STD_CHAN, rate=STD_RATE):
	print("Running RX script.")
	data = np.asarray(listen_record(chunk=chunk,channels=channels, rate=rate), dtype=np.int16) # Receive audio data
	freqs = to_dominant_freqs(data, chunk, rate) # Convert from raw data to frequencies
	print("RX FREQ DATA: ", freqs)
	bits = freqs_to_bits(freqs, STD_TX) # Convert from frequencies to bits
	print("RX BIT DATA: ", bits)
	data_bits, mode, filetype = bit_protocol_to_bytes(bits) # Extract
	return data_bits, mode, filetype


# ------------------------- TX - TRANSMIT -------------------------

# Envelop message bit-list in proper protocol headers
def to_protocol(payload: str | list[str],
                mode: str = '00',
                filetype: str = None,
                custom_length: list[str] = None) -> list[str]:
    # Start/End tokens
    start_syn = ["SYN"] * 20
    end_syn   = ["SYN"] * 3

    # Turn payload into bits
    if isinstance(payload, str):
        data_bits = bytes_to_bits(payload.encode('utf-8'))
    else:
        data_bits = payload[:]  # assume list of '0'/'1'

    # Mode is two bits: test-'00',ham-'01',data-'10',custom-'11'
    if mode not in ('00','01','10','11'):
        raise ValueError("mode must be one of '00','01','10','11'")
    mode_bits = list(mode)

    # Length field: 16‐bit for test/ham modes 00/01, 32‐bit for data mode 10, custom for 11
    if mode in ('00','01'):
        length_value = len(data_bits)
        len_bits = list(f"{length_value & 0xFFFF:016b}")
    elif mode == '10':
        length_value = len(data_bits)
        len_bits = list(f"{length_value & 0xFFFFFFFF:032b}")
    else:  # '11'
        if custom_length is None:
            raise ValueError("custom_length must be provided for mode '11'")
        len_bits = custom_length

    # Add type bits if in data mode
    type_bits = []
    if mode == '10':
        if not filetype:
            raise ValueError("filetype is required for DATA mode")
        type_bits = bytes_to_bits(filetype.encode('utf-8'))

    # Calc checksum for data
    checksum_bits = calc_checksum(data_bits)

    # Return the assembled data wrapped in protocol
    return (
        start_syn
      + mode_bits
      + len_bits
      + type_bits
      + checksum_bits
      + data_bits
      + end_syn
    )



#  Transfer between bit list and numpy audio array
def to_transmit_audio(bits: list, time_factor=STD_TX, rate=STD_RATE):
	# If bits values are not accepted, throw error
	i = 0
	for bit in bits:
		if bit not in frequencies.keys():  # Check if bits are fine for transmit
			raise Exception(f"ValueError - Unacceptable value for transmit at index {i}.")
		i += 1

	# Create audio_data return as numpy array
	audio_data = np.array([], dtype=np.float32)

	# Translate bits into audio data
	for bit in bits:
		frequency = frequencies.get(bit)  # Get assigned freq for bit data
		tone = generate_sine_wave(frequency, time_factor, rate)  # Generate wave based on bit

		audio_data = np.concatenate((audio_data, tone))  # Add to data

	audio_data = np.int16(audio_data * 32767)  # Return to 16-bit

	return audio_data

def handle_tx(data = "I hate C#", mode: str = '10', filetype: str = "Text"):
	print("Running TX script.")
	print("TX message: ",  data)
	bit_data = bytes_to_bits(bytes(data, 'utf-8'))  # Translation demonstration for input.
	print(bit_data)
	msg = to_protocol(bit_data, mode, filetype)  # TEST MODE -> Send 'Hello World!'
	print(msg)
	audio_data = to_transmit_audio(msg, STD_TX, rate=STD_RATE)
	play_audio(audio_data)


# Play a given numpy array that has been processed by the to_transmit_audio function
def play_audio(audio_data: np.ndarray, rate=STD_RATE):
	p = pyaudio.PyAudio()
	stream = p.open(format=pyaudio.paInt16,
					channels=1,
					rate=rate,
					output=True)
	stream.write(audio_data.tobytes())  # Directly pass the audio data as bytes
	stream.stop_stream()
	stream.close()
	p.terminate()

def ham_msg(pre: str = None, call: str = "4X5KD", suff: str = None, qth: tuple = (0.0, 0.0), time: str = "00:00:00"):
	# Prefix is for example 4X/
	# QTH is location, standard lon:lat. Suff (Suffix) is like /M, /P, /MM etc.\
	# Basic format for HAM mode is: Pre/Call/Suff|QTH|UTC
	# Time is UTC or more accurately unix time

	pre_txt = ""
	suff_txt = ""
	if pre:
		pre_txt = pre + "/"
	if suff:
		suff_txt = "/" + suff

	data_to_send = pre_txt + call + suff_txt + "|" + str(qth[0]) + ":" + str(qth[1]) + "|" + time
	return data_to_send