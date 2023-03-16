#!/usr/bin/env python3

import argparse
import threading
import time

import numpy as np
import pyaudio
import whisper
from pynput import keyboard


class SpeachToText:
    def __init__(self) -> None:
        args = self.process_args()

        self.p = pyaudio.PyAudio()

        # find the index of the specified device
        device_index = None
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['name'] == args.mic_device:
                device_index = info['index']
                break

        if device_index is None:
            self.p.terminate()
            raise ValueError(f'Could not find audio device named {args.mic_device}')

        # open the audio stream
        self.chunk_size = 512

        # print that the mic is loading in orange which will later be overwritten with mic ready in green
        print('\033[93m{}\033[00m'.format('loading mic...'), end='', flush=True)

        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=16000,
                                  input_device_index=device_index,
                                  input=True,
                                  frames_per_buffer=self.chunk_size)

        # overwrite the last print statement with mic ready in green
        print('\r\x1b[K\033[92m{}\033[00m'.format('mic ready!'))

        # print loading model in orange which will later be overwritten
        print('\033[93m{}\033[00m'.format('loading model...'), end='', flush=True)

        start_time = time.time()

        # load the whisper model
        self.model = whisper.load_model(name=args.model_name, device=args.inference_device)

        # make first inference on real data faster by forcing the model to finish loading since in_memory does not seem to fully preload the model
        self.model.transcribe(np.zeros(201, dtype=np.float32))

        end_time = time.time()

        # overwrite the last print statement with model ready in green and the time in cyan
        print('\r\x1b[K\033[92m{}\033[00m  \033[96m{:.2f}\033[00m seconds'.format('model ready!', end_time - start_time))

        # setup pynput
        self.keyboard = keyboard.Controller()

        # Set the activation key
        self.activation_key_pressed = False
        self.listener_thread = None

        # ignore input if the system is currently typing to avoid typing the activation key
        self.currently_typing = False

        # list of the frames the audio stream has read
        self.frames = []

    # make destructor to close the stream and terminate the pyaudio instance
    def __del__(self):
        # check if the thread is still running
        if hasattr(self, 'listener_thread') and self.listener_thread is not None and self.listener_thread.is_alive():
            print('thread still running')
            print(f'thread: {self.listener_thread}')

        # if there is a stream open close it
        if hasattr(self, 'stream') and self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'p') and self.p is not None:
            self.p.terminate()

    # this function processes the arguments and returns them
    def process_args(self):
        # get the args
        parser = argparse.ArgumentParser()
        # add general description
        parser.description = 'a small script that types what you say using whisper while holding a hotkey'
        parser.add_argument('--model_name', type=str, default='base.en', choices=['tiny.en', 'tiny', 'base.en', 'base', 'small.en',
                            'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large'], help='the name of the whisper model to use')
        parser.add_argument('--mic_device', type=str, default='default', help='the name of the pyaudio input device to use')
        parser.add_argument('--inference_device', type=str, default=None,
                            help='the device to run the inference on. can be cpu, cuda, or cuda:<device number> will automatically select the best device if not specified')
        parser.add_argument('--activation_key', type=str, default='<ctrl_r>', help='the key to use for push to talk. can be like <ctrl_r> or <alt_l> or <f1> or e or 1 or 2 or 3 etc')
        args = parser.parse_args()

        # print the model
        print(f'using model: \033[96m{args.model_name}\033[00m')

        try:
            hotkey_set = keyboard.HotKey.parse(args.activation_key)

            if len(hotkey_set) > 1:
                print('\033[91monly one key is supported right now\033[00m')
                exit(1)

            self.activation_key = hotkey_set[0]

            print(f'using key: \033[96m{self.activation_key}\033[00m')
        except ValueError:
            print('\033[91minvalid activation key\033[00m')
            parser.print_help()

        return args

    # runs the model on the frames
    def infer(self, frames):
        # a np array containing the audio waveform
        data = b''.join(frames)
        data = np.frombuffer(data, dtype=np.int16)

        data_to_transcribe = data.copy().flatten().astype(np.float32) / 32768.0

        # make sure the data is long enough or that anything exists at all
        if len(data_to_transcribe) <= 200:
            return ''

        whisper_output = self.model.transcribe(data_to_transcribe)

        # return just the text
        return whisper_output['text']

    # listens to the audio stream and then processes the frames and types the output text
    def listen(self):
        self.activation_key_pressed = True

        # print listening in cyan
        print()
        print('\033[96m{}\033[00m'.format('listening...'))
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

        # strip leading whitespace
        output_text = output_text.lstrip()

        # check if the output text is empty or is just periods
        if output_text == '' or output_text == '.' * len(output_text):
            print('nothing detected')
            self.activation_key_pressed = False
            return

        # remove all the trailing periods but also handle the case where there is only periods
        while output_text[-1] == '.':
            output_text = output_text[:-1]
            if output_text == '':
                print('nothing detected')
                self.activation_key_pressed = False
                return

        # convert the text to lowercase
        output_text = output_text.lower()

        print(output_text)

        # type the output text
        self.currently_typing = True
        self.keyboard.type(output_text)
        self.currently_typing = False

        # reset the activation key
        self.activation_key_pressed = False

    # called when a key is pressed
    def on_press(self, key):
        # ignore input if the system is currently typing to avoid typing the activation key
        if self.currently_typing:
            return

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
        print('Exiting...')
