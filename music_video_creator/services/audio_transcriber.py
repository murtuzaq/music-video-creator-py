import shutil


class AudioTranscriber:
    def transcribe(self, audio_path):
        self.__validate_ffmpeg()

        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True)

        words = []
        for segment in result.get("segments", []):
            for word in segment.get("words", []):
                clean = word["word"].strip()
                if clean:
                    words.append({
                        "text": clean,
                        "start": word["start"],
                        "end": word["end"],
                    })

        return words

    def __validate_ffmpeg(self):
        if not shutil.which("ffmpeg"):
            raise EnvironmentError("ffmpeg is not installed...")
