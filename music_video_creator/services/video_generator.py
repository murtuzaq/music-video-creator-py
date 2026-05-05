class VideoGenerator:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback

    def generate(self, jobs, audio_path, out_path):
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration

        load_times = [0.0] + [load_time for _, load_time in jobs[1:]]
        if load_times[-1] >= audio_duration:
            raise ValueError("Last image load time is after audio end.")

        durations = self._get_durations(load_times, audio_duration)
        clips = self._get_image_clips(jobs, durations)

        video = concatenate_videoclips(clips, method="compose")
        if audio.duration > video.duration:
            audio = audio.subclipped(0, video.duration)
        video = video.with_audio(audio)

        self._set_status("Rendering video...")
        video.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, logger=None)

    def _get_durations(self, load_times, audio_duration):
        durations = []
        for index in range(len(load_times)):
            if index < len(load_times) - 1:
                durations.append(load_times[index + 1] - load_times[index])
            else:
                durations.append(audio_duration - load_times[index])
        return durations

    def _get_image_clips(self, jobs, durations):
        from moviepy import ImageClip

        clips = []
        for index, ((img_path, _), duration) in enumerate(zip(jobs, durations), 1):
            self._set_status(f"Processing image {index}/{len(jobs)}...")
            clip = ImageClip(img_path, duration=duration).with_fps(24)
            clips.append(clip)
        return clips

    def _set_status(self, message):
        if self.status_callback is not None:
            self.status_callback(message)
