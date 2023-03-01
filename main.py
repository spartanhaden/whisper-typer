#!/usr/bin/env python3

import numpy as np
import pyaudio
import whisper
from pynput import keyboard


class SpeachToText:
    def __init__(self, device_name='default', model_name='base.en') -> None:
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
        self.chunk_size = 512

        print()
        # print ready in green
        print("\033[92m{}\033[00m".format("ready!"))

        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=16000,
                                  input_device_index=device_index,
                                  input=True,
                                  frames_per_buffer=self.chunk_size)

        # setup whisper
        self.model = whisper.load_model(model_name)

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

        whisper_output = self.model.transcribe(data_to_transcribe)

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


if __name__ == '__main__':
    SpeachToText().run()
