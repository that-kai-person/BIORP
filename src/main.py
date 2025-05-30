import BIORP_Utilities as brp
import numpy as np
import pyaudio
import tkinter

# STANDARD PARAMETERS

STD_FORMAT = brp.STD_FORMAT
STD_CHUNK = brp.STD_CHUNK
STD_CHAN = brp.STD_CHAN
STD_RATE = brp.STD_RATE
STD_TX = brp.STD_TX
frequencies = brp.frequencies

# SAMPLE BIT DATA TRANSMIT
i = input("TEST/DEBUG SCRIPT - RX or TX? ")

if i.lower() == "rx":
    print("Running RX test script.")
    listen_data = np.asarray(brp.listen_record(), dtype=np.int16)
    i = input("Awaiting input to playback.")
    brp.play_audio(listen_data)

    print("CHECKING VALIDITY")


    freqs = brp.to_dominant_freqs(listen_data, STD_CHUNK, STD_RATE)
    print("RX FREQS: ", freqs)
    bits = brp.freqs_to_bits(freqs, STD_TX)
    print("RX BITS:", bits)
    rx_bytes = brp.bit_protocol_to_bytes(bits)
    print("BYTE DATA RECEIVED: ", rx_bytes)
    print("DECODED DATA: ", rx_bytes.decode('utf-8', errors='replace'))

    known_data = "I hate C#" # Known sample data
    true_data_bytes = bytes(known_data, 'utf-8')
    print("BYTE DATA OF KNOWN MESSAGE: ", true_data_bytes)
    true_data_bits = brp.bytes_to_bits(true_data_bytes)
    true_data_freqs = brp.to_protocol(true_data_bits, mode='10', filetype="Text")
    print("TRUE DATA FREQS: ", true_data_freqs)

    print("NO. OF DIFF BETWEEN KNOWN AND RX: ", len(brp.compare_lists(rx_bytes, true_data_bytes)["common_elements"]))
    print("DIFF LIST BETWEEN KNOWN AND RX: ", brp.compare_lists(rx_bytes, true_data_bytes)["differences"])
    

if i.lower() == "tx":
    print("Running TX test script.")
    data = "I hate C#"
    print("TX message: " + data)
    bit_data = brp.bytes_to_bits(bytes(data, 'utf-8'))  # Translation demonstration for input.
    print(bit_data)
    msg = brp.to_protocol(bit_data, mode='01', filetype="Text")  # TEST MODE -> Send 'Hello World!'
    print(msg)
    audio_data = brp.to_transmit_audio(msg, STD_TX, rate=STD_RATE)
    brp.play_audio(audio_data)

"""

    TODO LIST
        - RECEIVE/RECORD:
            * Listen & record function
                > Collect 3 secs of audio & analyze to know if busy XV
                > Once busy, record from *start* of message V
                > End recording after END (And see not busy after) V
            * Decode audio->bits
                > Transform from raw audio frames to dominant freq frames using fft V
                ? Use SYNC message to slice message to the format & set tx rate (Left as optional)
            * Dissect format and output file to preview/download
        - TRANSMIT
            * Envelop data with protocol V
            * Analyze files (Text, .txt, .jpeg/.jpg/.png and reduce file size
                (Transmit only data, name, size, aspect ratio etc.)
        - USER INTERFACE
            * Transmit/Receive pages V
            * Current audio level in mic
            * Play to user current input audio from mic
            * Play to user transmitted audio when transmitting
            * File upload for tx
            * File preview for rx
            * Mode select (HAM/DATA)
            * Select download folder for rx
            

"""