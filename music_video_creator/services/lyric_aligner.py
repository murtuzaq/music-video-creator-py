class LyricAligner:
    def align(self, audio_path, lyrics_words):
        import whisper

        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True)
        transcribed_words = self.__get_transcribed_words(result)
        return self.__align_words(lyrics_words, transcribed_words)

    def __get_transcribed_words(self, result):
        transcribed_words = []
        for segment in result.get("segments", []):
            for word in segment.get("words", []):
                clean = word["word"].strip('.,!?')
                if clean:
                    transcribed_words.append({
                        "text": clean.lower(),
                        "start": word["start"],
                        "end": word["end"]
                    })
        return transcribed_words

    def __align_words(self, lyrics_words, transcribed_words):
        aligned_words = []
        transcribed_index = 0

        for original_word in lyrics_words:
            best_match, best_score, best_index = self.__find_best_match(
                original_word,
                transcribed_words,
                transcribed_index
            )

            if best_match and best_score > 0.5:
                aligned_words.append({
                    "text": original_word["text"],
                    "start": best_match["start"],
                    "end": best_match["end"]
                })
                transcribed_index = best_index + 1
            else:
                aligned_words.append(original_word)

        return aligned_words

    def __find_best_match(self, original_word, transcribed_words, transcribed_index):
        original_text = original_word["text"].lower()
        best_match = None
        best_score = -1
        best_index = transcribed_index
        search_end = min(transcribed_index + 30, len(transcribed_words))

        for index in range(transcribed_index, search_end):
            score = self.__word_similarity(original_text, transcribed_words[index]["text"])
            if score > best_score:
                best_score = score
                best_match = transcribed_words[index]
                best_index = index

        return best_match, best_score, best_index

    def __word_similarity(self, left_word, right_word):
        if not left_word or not right_word:
            return 0.0

        left_set = set(left_word)
        right_set = set(right_word)
        return len(left_set & right_set) / max(len(left_set), len(right_set))
