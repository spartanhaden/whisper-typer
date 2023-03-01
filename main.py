#!/usr/bin/env python3

import threading
import time

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

        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=16000,
                                  input_device_index=device_index,
                                  input=True,
                                  frames_per_buffer=self.chunk_size)

        # setup whisper
        self.model = whisper.load_model(model_name)

        # setup pynput
        self.keyboard = keyboard.Controller()

        # print ready in green
        print("\033[92m{}\033[00m".format("ready!"))

        # F16 key
        self.activation_key = keyboard.KeyCode.from_vk(269025095)
        self.activation_key_pressed = False
        self.listener_thread = None

        # list of the frames the audio stream has read
        self.frames = []

    # make destructor to close the stream and terminate the pyaudio instance
    def __del__(self):
        # check ifthe thread is still running
        if self.listener_thread is not None and self.listener_thread.is_alive():
            print('thread still running')
            print(f'thread: {self.listener_thread}')

        # if there is a stream open close it
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        if self.p is not None:
            self.p.terminate()

    # runs the model on the frames
    def infer(self, frames):
        # a np array containing the audio waveform
        data = b''.join(frames)
        data = np.frombuffer(data, dtype=np.int16)

        data_to_transcribe = data.copy().flatten().astype(np.float32) / 32768.0

        whisper_output = self.model.transcribe(data_to_transcribe)

        # return just the text
        return whisper_output["text"]

    # listens to the audio stream and then processes the frames and types the output text
    def listen(self):
        self.activation_key_pressed = True

        # print listening in cyan
        print()
        print("\033[96m{}\033[00m".format("listening..."))
        self.stream.start_stream()

        while self.activation_key_pressed:
            frames_to_read = self.stream.get_read_available()
            if frames_to_read > 0:
                data = self.stream.read(frames_to_read, exception_on_overflow=False)
                self.frames.append(data)

            time.sleep(0.001)

        # stop the stream
        self.stream.stop_stream()

        # process the frames
        output_text = self.infer(self.frames)

        # reset the frames
        self.frames = []

        # check if the output text is empty
        if output_text == '':
            print('nothing detected')
            self.activation_key_pressed = False
            return

        # remove the leading space
        output_text = output_text[1:]

        # remove the trailing period if there is one
        output_text = output_text[:-1] if output_text[-1] == '.' else output_text

        # convert the text to lowercase
        output_text = output_text.lower()

        print(output_text)

        # type the output text
        self.keyboard.type(output_text)

        # reset the activation key
        self.activation_key_pressed = False

    # called when a key is pressed
    def on_press(self, key):
        # check if the designated key was pressed and that the key is not already being pressed
        if key == self.activation_key and not self.activation_key_pressed:
            # check if the thread is already running
            if self.listener_thread is not None and self.listener_thread.is_alive():
                print('thread already running')
                return

            # start a new thread of the listen function
            self.listener_thread = threading.Thread(target=self.listen)
            self.listener_thread.start()

    # called when a key is released
    def on_release(self, key):
        # check if the designated key was released
        if key == self.activation_key:
            self.activation_key_pressed = False

    def run(self):
        # start the keyboard listener
        keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        keyboard_listener.start()

        # wait for the keyboard listener to finish
        keyboard_listener.join()


if __name__ == '__main__':
    try:
        SpeachToText().run()
    except KeyboardInterrupt:
        print("Exiting...")
