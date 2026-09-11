"""Voice check-in transcription endpoint tests; Whisper inference is mocked."""
import unittest
from unittest.mock import patch
import test_monitoring as t


class VoiceEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t.ChatMonitoringTests.setUpClass()

    setUp = t.ChatMonitoringTests.setUp
    headers = t.ChatMonitoringTests.headers

    def test_victim_can_transcribe_supported_audio(self):
        result = {
            "transcript": "I feel overwhelmed and I have not been sleeping.",
            "language": "en",
            "language_probability": 0.99,
        }
        with patch("app.voice.transcribe_audio", return_value=result) as transcribe:
            response = self.client.post(
                "/api/victim/voice/transcribe",
                headers={**self.headers(), "Content-Type": "audio/webm;codecs=opus"},
                content=b"fake-webm-test-bytes",
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["transcript"], result["transcript"])
        self.assertEqual(response.json()["language"], "en")
        transcribe.assert_called_once()

    def test_voice_endpoint_is_victim_only_and_live_account_checked(self):
        with patch("app.voice.transcribe_audio") as transcribe:
            response = self.client.post(
                "/api/victim/voice/transcribe",
                headers={**self.headers(3, "counsellor"), "Content-Type": "audio/webm"},
                content=b"audio",
            )
            self.assertEqual(response.status_code, 403)
            response = self.client.post(
                "/api/victim/voice/transcribe",
                headers={**self.headers(999, "victim"), "Content-Type": "audio/webm"},
                content=b"audio",
            )
            self.assertEqual(response.status_code, 401)
        transcribe.assert_not_called()

    def test_rejects_bad_type_empty_and_no_speech(self):
        bad = self.client.post(
            "/api/victim/voice/transcribe",
            headers={**self.headers(), "Content-Type": "text/plain"},
            content=b"audio",
        )
        self.assertEqual(bad.status_code, 415)

        empty = self.client.post(
            "/api/victim/voice/transcribe",
            headers={**self.headers(), "Content-Type": "audio/webm"},
            content=b"",
        )
        self.assertEqual(empty.status_code, 400)

        with patch("app.voice.transcribe_audio", return_value={"transcript": "", "language": None, "language_probability": None}):
            no_speech = self.client.post(
                "/api/victim/voice/transcribe",
                headers={**self.headers(), "Content-Type": "audio/webm"},
                content=b"silence",
            )
        self.assertEqual(no_speech.status_code, 422)

    def test_transcription_failure_is_controlled(self):
        from app.voice_service import VoiceTranscriptionError
        with patch("app.voice.transcribe_audio", side_effect=VoiceTranscriptionError("Voice transcription failed.")):
            response = self.client.post(
                "/api/victim/voice/transcribe",
                headers={**self.headers(), "Content-Type": "audio/webm"},
                content=b"audio",
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Voice transcription failed.")


if __name__ == "__main__":
    unittest.main()
