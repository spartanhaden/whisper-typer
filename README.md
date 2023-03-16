# whisper-typer

A small script that types what you say using whisper while holding a hotkey

I have only tested this on Linux, but it should work on Windows and Mac as well

## Usage

Install requirements:

```bash
pip3 install -r requirements.txt
```

Run the script:

```bash
python3 main.py
```

## Command line options

```bash
python3 main.py --help
```

```
usage: main.py [-h] [--model_name {tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large}] [--mic_device MIC_DEVICE] [--inference_device INFERENCE_DEVICE] [--activation_key ACTIVATION_KEY]

a small script that types what you say using whisper while holding a hotkey

options:
  -h, --help            show this help message and exit
  --model_name {tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large}
                        the name of the whisper model to use
  --mic_device MIC_DEVICE
                        the name of the pyaudio input device to use
  --inference_device INFERENCE_DEVICE
                        the device to run the inference on. can be cpu, cuda, or cuda:<device number> will automatically select the best device if not specified
  --activation_key ACTIVATION_KEY
                        the key to use for push to talk. can be like <ctrl_r> or <alt_l> or <f1> or e or 1 or 2 or 3 etc
```

Defaults

```yaml
model_name: "base.en"
mic_device: "default"
inference_device: None
activation_key: "<ctrl_r>"
```
