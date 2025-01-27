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

    SYN - Sync message. 10 SYN tokens.

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
STD_CHUNK = 1024  # Sampling chunk for RX
STD_CHAN = 1  # 1 for mono, 2 for stereo. UV-K6 does NOT work with stereo.
STD_RATE = 44100  # Sample rate for RX
STD_TX = 1/100  # 100 bit per second (BpSec) TX rate

frequencies = {"0": 450,
               "1": 550,
               "SYN": 500}


def bytes_to_bits(input: bytes):  # Convert the bytes received from pyaudio to bits for files
    bit_list = []
    for byte in input:
        # Convert the byte to an 8-bit binary string (e.g., 0b10101001 -> '10101001')
        bits = format(byte, '08b')
        # Add each bit to the bit_list (you can also use a list comprehension here)
        bit_list.extend(bits)

    return bit_list


def rms(input: list):
    return np.sqrt(np.mean(np.square(input)))


def peak_amplitude(input: list):
    return np.max(np.abs(input))


def generate_sine_wave(frequency, duration, rate):
    t = np.linspace(0, duration, int(rate * duration), endpoint=False)
    return np.sin(2 * np.pi * frequency * t)


def calc_checksum(bits: list):
    # Calculate a 16-bit checksum for a given list of bits.
    total = 0
    # Will take 16-bit chunks, convert them into an integer, then sum it into total
    for i in range(0, len(bits), 16):
        chunk = bits[i:i + 16]
        total += int("".join(chunk), 2)

    checksum_value = total % 65536  # Modulo into 16-bit number
    checksum = list(f"{checksum_value:016b}")  # Return a list containing the 16-bit binary number of the checksum

    return checksum


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


def round_to_freqs(data: list):
    frequencies_list = [450, 500, 550]
    rounded_list = []
    for cell in data:
        rounded_cell = min(frequencies_list, key=lambda x: abs(cell - x))
        rounded_list.append(rounded_cell)
    return rounded_list


# RX - RECEIVE


def record_audio(record_seconds, chunk=STD_CHUNK, format=STD_FORMAT, channels=STD_CHAN, rate=STD_RATE):
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
    # Create a buffer to store last 3 secs of audio data
    buffer_size = rate * 3
    buffer = np.zeros(buffer_size, dtype=np.int16)

    p = pyaudio.PyAudio()
    stream = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)

    recording = False
    return_audio = []

    while True:
        # Take in data from stream
        data = stream.read(chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)

        # Roll back buffer for new data
        buffer[:] = np.roll(buffer, -chunk)
        buffer[-chunk:] = audio_data

        # See if exists audio activity using rms
        if rms(buffer.tolist()) >= thresh:
            if not recording:
                # New audio activity detected
                recording = True
                return_audio = buffer.copy().tolist()
            return_audio.extend(audio_data)

        elif recording:
            # Audio is beneath thresh at end of record
            recording = False
            break

    # Close stream
    stream.stop_stream()
    stream.close()
    p.terminate()

    return return_audio


def chunk_to_dominant_freq(audio_data: list, rate=STD_RATE):
    length = len(audio_data)

    # Make input data into np array
    data = np.array(audio_data)
    # Compute FFT result - a list of all different frequencies in the given audio section as complex numbers
    fft_out = np.fft.fft(data)
    # Get frequencies for the section
    freqs = np.fft.fftfreq(length, d=1 / rate)  # d being the period of sampling
    # Get different magnitudes for each frequency
    magnitudes = np.abs(fft_out)
    # Turn all frequencies/magnitudes positive (Symmetry of FFT)
    freqs = freqs[:length // 2]
    magnitudes = magnitudes[:length // 2]

    # Get index of "loudest" frequency and get it
    dominant_freq_idx = np.argmax(magnitudes)
    dominant_freq = freqs[dominant_freq_idx]

    return dominant_freq


def to_dominant_freqs(audio_data: list, chunk=STD_CHUNK, rate=STD_RATE):
    freqs = []
    for i in range(0, len(audio_data) + chunk, chunk):
        if i >= len(audio_data):
            break
        freqs.append(chunk_to_dominant_freq(audio_data[i:i + chunk], rate=rate))

    return freqs


def find_tx_rate(freqs: list):
    print("WIP")
    return


def freqs_to_bits(freqs: list, tx_rate: int = STD_TX):
    bits = []
    return bits


def handle_rx(chunk=STD_CHUNK, format=STD_FORMAT, channels=STD_CHAN, rate=STD_RATE):
    data = listen_record(chunk, format, channels, rate)
    freqs = to_dominant_freqs(data, chunk, rate)
    return


# TX - TRANSMIT

# Envelop message bit-list in proper protocol headers
def to_protocol(data_bits: list, mode: str = "00", filetype: str = None, custom_length: int = None):
    start_syn = ["SYN", "SYN", "SYN", "SYN", "SYN", "SYN", "SYN", "SYN", "SYN", "SYN"]
    end_syn = ["SYN", "SYN", "SYN"]

    match mode:
        case "00":
            len_bits = bytes_to_bits(bytes(ctypes.c_int16(len(data_bits))))
        case "01":
            len_bits = bytes_to_bits(bytes(ctypes.c_int16(len(data_bits))))
        case "10":
            len_bits = bytes_to_bits(bytes(ctypes.c_int32(len(data_bits))))
        case "11":
            len_bits = custom_length
        case _:
            len_bits = 0

    print(len_bits)
    mode_bits = bytes_to_bits(bytes(mode, 'utf-8'))
    type_bits = bytes_to_bits(bytes(filetype, 'utf-8'))
    checksum_bits = calc_checksum(data_bits)

    return start_syn + mode_bits + len_bits + type_bits + checksum_bits + data_bits + end_syn


#  Transfer between bit list and numpy audio array
def to_transmit_audio(bits: list, time_factor=STD_TX, rate=STD_RATE):
    # If bits values are not accepted, throw error
    i = 0
    for bit in bits:
        if bit not in frequencies.keys():
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

def ham_msg(call: str = "4X5KD", aff: str = None, qth: tuple = (0, 0)):
    # Affix is for example 4X/KK7UX
    # QTH is location, standard lon/lat. Add is like /M, /P, /MM etc.\

    bits = []
    return bits


def handle_tx(data, time_factor):
    return
