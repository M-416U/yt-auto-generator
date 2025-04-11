import torch
from TTS.api import TTS
import os
import uuid
import wave

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tts_model = None


def get_tts_model():
    global tts_model
    if tts_model is None:
        try:
            print("Initializing TTS...")
            tts_model = TTS(
                # model_name="tts_models/en/multi-dataset/tortoise-v2",
                # model_name="tts_models/en/ljspeech/vits",
                model_name="tts_models/en/vctk/vits",
                # model_name="tts_models/multilingual/multi-dataset/your_tts",
                # model_name="tts_models/en/ljspeech/tacotron2-DDC",
                # model_path="./resources/tts/tts_models--en--ljspeech--tacotron2-DDC/model.pth",
                # config_path="./resources/tts/tts_models--en--ljspeech--tacotron2-DDC/config.json",
                progress_bar=True,
            )
            tts_model.to(device)
        except Exception as e:
            print(f"Error initializing TTS model: {e}")
            return None
    return tts_model


def text_to_speech(text, output_dir="output_audio", speaker="p228"):
    model = get_tts_model()
    if model is None:
        raise RuntimeError("TTS model failed to initialize")
    try:
        # Create output directory if not exists
        os.makedirs(output_dir, exist_ok=True)
        # Preprocess text
        text = text.replace("\n", " ").strip()
        # Remove emojis and special characters
        text = "".join(char for char in text if ord(char) < 65536).lower()
        # Ensure minimum text length
        if len(text) < 10:
            text = text + " " + text  # Duplicate short text

        # Generate a unique filename
        filename = f"{uuid.uuid4().hex}.wav"
        file_path = os.path.join(output_dir, filename)

        # Convert text to speech and save to file
        print(f"Converting text to speech: {text[:50]}...")
        model.tts_to_file(text=text, file_path=file_path, speaker=speaker)
        print("Audio generation completed!")

        # Get audio duration from the saved file
        with wave.open(file_path, "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)

        return file_path, duration
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None


if __name__ == "__main__":
    print("Running text-to-speech test...")
    text = "this is a test text to speach"
    audio_file = text_to_speech(text)
    if audio_file:
        print(f"Audio file saved to: {audio_file}")
    else:
        print("Failed to generate audio file")
