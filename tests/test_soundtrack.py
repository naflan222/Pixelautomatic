import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from pixelhouse.soundtrack import create_soundtrack

class SoundtrackTests(unittest.TestCase):
    def test_original_score_is_audible_stereo_and_has_headroom(self):
        with tempfile.TemporaryDirectory() as directory:
            target=create_soundtrack(Path(directory)/'score.wav',seed=12,duration=1)
            with wave.open(str(target),'rb') as sound:
                self.assertEqual(sound.getnchannels(),2)
                self.assertEqual(sound.getframerate(),44100)
                self.assertEqual(sound.getnframes(),44100)
                samples=array('h',sound.readframes(sound.getnframes()))
            rms=math.sqrt(sum(v*v for v in samples)/len(samples))
            self.assertGreater(rms,1000)
            self.assertLessEqual(max(abs(v) for v in samples),23501)
            self.assertEqual(samples[0],0)
            self.assertLess(abs(samples[-1]),30)
            self.assertNotEqual(samples[0::2],samples[1::2])
