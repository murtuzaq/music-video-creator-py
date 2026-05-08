class AppState:
    def __init__(self):
        self.audio_path = None
        self.image_entries = []
        self.generating = False
        self.transcription_words = []
        self.switch_points = []
        self.project_tree = None   # nested dict: {"type","name","path","children"}
