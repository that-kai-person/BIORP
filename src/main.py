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
    rx_data, mode, filetype = brp.handle_rx()
    print("DATA: ", rx_data)
    print("MODE: ", mode)
    print("FILE TYPE:", filetype)
    

if i.lower() == "tx":
    brp.handle_tx()

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