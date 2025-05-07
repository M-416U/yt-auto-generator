from TTS.utils.synthesizer import save_wav
import torch
import numpy as np
import os
import uuid
import wave
import json
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import re
from pydub import AudioSegment

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tts_model = None

config = XttsConfig()
config.load_json("./resources/tts/xtts_v2/config.json")


def get_tts_model():
    global tts_model
    if tts_model is None:
        try:
            print("Initializing TTS...")
            model = Xtts.init_from_config(config)
            model.load_checkpoint(
                config, checkpoint_dir="./resources/tts/xtts_v2/", eval=True
            )
            # model.cuda()
            tts_model = model
        except Exception as e:
            print(f"Error initializing TTS model: {e}")
            return None
    return tts_model


def load_voice_overs():
    """Load voice overs from the voice_overs.json file"""
    try:
        with open("voice_overs.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading voice overs: {e}")
        return {}


def get_voice_sample(voice_id, language="en"):
    """Get the voice sample path for a given voice ID and language"""
    voice_overs = load_voice_overs()
    default_sample = "./resources/audio.wav"

    # First check if the file exists in the voice_overs data
    if language in voice_overs:
        for voice in voice_overs[language]["voices"]:
            if voice["id"] == voice_id:
                sample_path = voice.get("sample", default_sample)
                if os.path.exists(sample_path):
                    return sample_path
                else:
                    print(
                        f"Warning: Sample file {sample_path} not found, using default"
                    )

    # If we reach here, either the voice wasn't found or the sample doesn't exist
    # Check if the default sample exists
    if os.path.exists(default_sample):
        return default_sample

    # If even the default doesn't exist, use the first available sample file in resources
    resources_dir = "./resources"
    if os.path.exists(resources_dir):
        for root, _, files in os.walk(resources_dir):
            for file in files:
                if file.endswith((".wav", ".mp3")):
                    return os.path.join(root, file)

    # If we still can't find anything, raise a more helpful error
    raise FileNotFoundError(
        f"No voice sample files found. Please ensure voice sample files exist in {resources_dir} or the path specified in voice_overs.json"
    )


def split_text_into_chunks(text, max_tokens):
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_tokens):
        chunk = " ".join(words[i : i + max_tokens])
        chunks.append(chunk)

    return chunks


def synthesize_chunk(text, model, config, speaker_wav, language):
    """Synthesize a single chunk of text"""
    outputs = model.synthesize(
        text,
        config,
        speaker_wav=speaker_wav,
        language=language,
    )

    if isinstance(outputs, dict):
        if "wav" in outputs:
            return outputs["wav"]
        else:
            for key, value in outputs.items():
                if isinstance(value, (list, np.ndarray)) and not isinstance(
                    value, dict
                ):
                    return value
            raise ValueError(
                f"Could not find audio data in outputs: {list(outputs.keys())}"
            )
    else:
        return outputs


def text_to_speech(text, output_dir="output_audio", speaker="1", language="en"):
    model = get_tts_model()
    if model is None:
        raise RuntimeError("TTS model failed to initialize")
    try:
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique filename for the final output
        filename = f"{uuid.uuid4().hex}.wav"
        file_path = os.path.join(output_dir, filename)

        # Get the voice sample path
        speaker_wav = get_voice_sample(speaker, language)

        print(f"Converting text to speech (length: {len(text)} chars)...")
        print(f"Using voice: {speaker}, language: {language}")

        # Split text into manageable chunks
        text_chunks = split_text_into_chunks(
            text,
            max_tokens=15,
        )
        print(f"Text split into {len(text_chunks)} chunks")

        if len(text_chunks) == 0:
            raise ValueError("No valid text chunks to process")

        if len(text_chunks) == 1:
            # If only one chunk, process normally
            wav = synthesize_chunk(text_chunks[0], model, config, speaker_wav, language)
            save_wav(wav=wav, path=file_path, sample_rate=22050)
        else:
            # Process each chunk and combine
            temp_files = []

            for i, chunk in enumerate(text_chunks):
                print(f"Processing chunk {i+1}/{len(text_chunks)}")
                temp_filename = os.path.join(output_dir, f"temp_{uuid.uuid4().hex}.wav")

                wav = synthesize_chunk(chunk, model, config, speaker_wav, language)
                save_wav(wav=wav, path=temp_filename, sample_rate=22050)
                temp_files.append(temp_filename)

            # Combine audio files using pydub
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                segment = AudioSegment.from_wav(temp_file)
                combined += segment

            # Export combined audio
            combined.export(file_path, format="wav")

            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass

        print("Audio generation completed!")

        # Calculate duration
        with wave.open(file_path, "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)

        return file_path, duration
    except Exception as e:
        print(f"Error generating audio: {e}")
        import traceback

        traceback.print_exc()
        return None, 0


if __name__ == "__main__":
    print("Running text-to-speech test...")
    text = "It took me quite a long time to develop a voice and now that I have it I am not going to be silent."
    audio_file, duration = text_to_speech(text)
    if audio_file:
        print(f"Audio file saved to: {audio_file}")
        print(f"Duration: {duration} seconds")
    else:
        print("Failed to generate audio file")
