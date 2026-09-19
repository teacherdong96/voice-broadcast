# -*- coding: utf-8 -*-
"""语音播报封装：使用 pyttsx3 离线 TTS，在独立线程中播放，避免阻塞 UI。"""
import threading
import queue


class Speaker:
    def __init__(self, rate=180, volume=1.0):
        self.rate = rate
        self.volume = volume
        self._q = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._ready = False
        self._engine = None
        self._thread.start()

    def _worker(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)
            self._ready = True
        except Exception as e:
            print("TTS init failed:", e)
            return
        while True:
            text = self._q.get()
            if text is None:
                break
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as e:
                print("speak failed:", e)

    def speak(self, text):
        if not text:
            return
        self._q.put(text)

    def set_params(self, rate=None, volume=None):
        if rate is not None:
            self.rate = rate
        if volume is not None:
            self.volume = volume
        if self._engine:
            try:
                if rate is not None:
                    self._engine.setProperty("rate", rate)
                if volume is not None:
                    self._engine.setProperty("volume", volume)
            except Exception:
                pass

    def stop(self):
        try:
            self._q.put(None)
            if self._engine:
                self._engine.stop()
        except Exception:
            pass
