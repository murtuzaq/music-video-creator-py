class LyricFileLoader:
    def load(self, path):
        raw = self.__read_file(path)
        words = self.__split_words(raw)
        return self.__create_placeholder_transcription(words)

    def __read_file(self, path):
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    def __split_words(self, raw):
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        words = []

        for line in lines:
            for word in line.split():
                clean_word = word.strip('.,!?()[]{}"\'').strip()
                if clean_word:
                    words.append(clean_word)

        return words

    def __create_placeholder_transcription(self, words):
        transcription_words = []
        current_time = 0.0

        for word in words:
            transcription_words.append({
                "text": word,
                "start": round(current_time, 2),
                "end": round(current_time + 0.4, 2),
            })
            current_time += 0.5

        return transcription_words
