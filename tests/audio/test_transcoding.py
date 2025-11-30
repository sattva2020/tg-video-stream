import sys
import os
import unittest

# Make streamer package available to tests when running from repo root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'streamer')))
import audio_utils


class TestTranscodingDetection(unittest.TestCase):

    def test_get_transcoding_profile_by_extension(self):
        p = audio_utils.get_transcoding_profile('http://example.com/track.flac')
        self.assertIsNotNone(p)
        self.assertIn('ffmpeg_args', p)

        q = audio_utils.get_transcoding_profile('http://example.com/song.ogg')
        self.assertIsNotNone(q)
        self.assertIn('ffmpeg_args', q)

    def test_get_transcoding_profile_by_content_type(self):
        p = audio_utils.get_transcoding_profile('http://example.com/stream', content_type='audio/flac')
        self.assertIsNotNone(p)
        p2 = audio_utils.get_transcoding_profile('http://example.com/stream', content_type='application/ogg')
        self.assertIsNotNone(p2)


if __name__ == '__main__':
    unittest.main()
