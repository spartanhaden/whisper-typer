#!/usr/bin/env python3

import pickle
import pprint
import time
import wave

import numpy as np
import pyaudio
import whisper
from pynput import keyboard


class SpeachToText:
    def __init__(self, device_name) -> None:
        self.p = pyaudio.PyAudio()
        self.stream = None

        # find the index of the specified device
        device_index = None
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['name'] == device_name:
                device_index = info['index']
                break

        if device_index is None:
            raise ValueError(f"Could not find audio device named {device_name}")

        # open the audio stream
        self.CHUNK = 512
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        print()
        # print ready in green
        print("\033[92m{}\033[00m".format("ready!"))

        self.stream = self.p.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input_device_index=device_index,
                                  input=True,
                                  frames_per_buffer=self.CHUNK)

        # setup whisper
        self.model = whisper.load_model("base.en")

        self.keyboard = keyboard.Controller()

    # make destructor to close the stream and terminate the pyaudio instance
    def __del__(self):
        # if there is a stream open close it
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        if self.p is not None:
            self.p.terminate()

    # note that
    def infer(self, frames):
        # a np array containing the audio waveform
        data = b''.join(frames)
        data = np.frombuffer(data, dtype=np.int16)

        data_to_transcribe = data.copy().flatten().astype(np.float32) / 32768.0

        whisper_output = self.model.transcribe(data_to_transcribe, language="en")

        import pprint

        # pprint.pprint(result)
        # set the output text and remove the leading space
        output_text = whisper_output["text"][1:]
        print(output_text)

        self.keyboard.type(output_text)

        return output_text

    def run(self):
        current_keys = set()

        with keyboard.Listener(on_press=lambda key: current_keys.add(key), on_release=lambda key: current_keys.discard(key)) as listener:

            # F16 key
            activation_key = 269025095
            activation_key_pressed = False

            frames = []

            try:
                while True:

                    if keyboard.KeyCode.from_vk(activation_key) in current_keys:
                        if not activation_key_pressed:
                            print()
                            # print listening in cyan
                            print("\033[96m{}\033[00m".format("listening..."))
                            self.stream.start_stream()
                            activation_key_pressed = True
                        frames_to_read = self.stream.get_read_available()
                        if frames_to_read > 0:
                            data = self.stream.read(frames_to_read, exception_on_overflow=False)
                            frames.append(data)
                    elif activation_key_pressed:
                        # process the frames after the activation key is released
                        self.stream.stop_stream()
                        self.infer(frames)
                        frames = []
                        activation_key_pressed = False

            except KeyboardInterrupt:
                # handle the Ctrl+C interrupt
                print("Exiting...")


def graph_frames_from_pyaudio(frames):
    import matplotlib.pyplot as plt
    import numpy as np

    # get the audio data from the frames
    data = b''.join(frames)
    data = np.frombuffer(data, dtype=np.int16)

    # plot the audio data
    plt.plot(data)
    plt.show()


def get_devices():
    p = pyaudio.PyAudio()

    # list the devices
    print()
    for i in range(p.get_device_count()):
        print()
        pprint.pprint(p.get_device_info_by_index(i))


def pickle_frames(frames):
    data = b''.join(frames)
    data = np.frombuffer(data, dtype=np.int16)
    with open('frames.pickle', 'wb') as f:
        pickle.dump(data, f)


def unpickle_frames():
    print("Loading frames from pickle...")
    with open('frames.pickle', 'rb') as f:
        data = pickle.load(f)
    print("done loading")
    return data


if __name__ == '__main__':
    speech_to_text = SpeachToText('')
    speech_to_text.run()
