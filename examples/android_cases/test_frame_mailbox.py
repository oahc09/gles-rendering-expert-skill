"""Host execution of production mailbox; Android/GL driver is not emulated."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "surfacevideo/src/main/java/org/example/gleslab"


class FrameMailboxContract(unittest.TestCase):
    def test_callback_and_consumer_use_the_same_registration_gate(self):
        source = (PACKAGE / "ExternalSurfaceActivity.java").read_text()
        self.assertIn("registration = frames.register(consumer)", source)
        self.assertIn("if (frames.offer(registration, source)) view.requestRender()", source)
        self.assertIn("if(frames.take(consumer)){VideoInputGuard.acquireFrame", source)
        self.assertIn("synchronized void stopProducer() {\n            frames.retire();", source)
        self.assertEqual(source.count("stopProducer(); releaseConsumer();"), 2)
        self.assertIn("consumer.setOnFrameAvailableListener(null)", source)

    @unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "host JDK unavailable")
    def test_late_callback_and_context_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run([
                "javac", "--release", "17", "-Xlint:all", "-Werror", "-d", folder,
                str(PACKAGE / "FrameMailbox.java"),
                str(ROOT / "host-tests/FrameMailboxTest.java"),
            ], check=True, timeout=20)
            result = subprocess.run([
                "java", "-cp", folder, "org.example.gleslab.FrameMailboxTest",
            ], check=True, timeout=20, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), "PASS: SurfaceTexture registration mailbox")


if __name__ == "__main__":
    unittest.main()
