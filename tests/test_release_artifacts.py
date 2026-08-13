import json
import struct
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.references = []
        self.images_without_alt = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        for name in ("href", "src"):
            if name in attributes:
                self.references.append(attributes[name])
        if tag == "img" and "alt" not in attributes:
            self.images_without_alt.append(attributes.get("src", "<unknown>"))


def png_dimensions(path):
    with path.open("rb") as image:
        signature = image.read(24)
    if signature[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path} is not a PNG")
    return struct.unpack(">II", signature[16:24])


class ReleaseArtifactTests(unittest.TestCase):
    def test_plugin_manifest_release_metadata_and_assets(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["author"]["name"], "Ernie Brodeur")
        self.assertEqual(manifest["author"]["email"], "ebrodeur@ujami.net")
        self.assertEqual(manifest["license"], "GPL-3.0-only")
        self.assertEqual(manifest["repository"], "https://github.com/erniebrodeur/recovery")
        self.assertEqual(manifest["homepage"], "https://erniebrodeur.github.io/recovery/")

        interface = manifest["interface"]
        self.assertEqual(interface["developerName"], "Ernie Brodeur")
        self.assertEqual(interface["brandColor"], "#0D6764")
        self.assertIsInstance(interface["defaultPrompt"], list)
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)
        self.assertTrue(all(len(prompt) <= 128 for prompt in interface["defaultPrompt"]))

        expected_sizes = {
            "composerIcon": (512, 512),
            "logo": (1200, 320),
            "logoDark": (1200, 320),
        }
        for field, dimensions in expected_sizes.items():
            asset = ROOT / interface[field].removeprefix("./")
            self.assertTrue(asset.is_file(), f"missing {field}: {asset}")
            self.assertEqual(png_dimensions(asset), dimensions)

    def test_static_docs_local_references_and_fragments(self):
        document = ROOT / "docs" / "index.html"
        parser = DocumentParser()
        parser.feed(document.read_text())

        self.assertEqual(len(parser.ids), len(set(parser.ids)), "duplicate HTML id")
        self.assertEqual(parser.images_without_alt, [])

        ids = set(parser.ids)
        for reference in parser.references:
            parsed = urlsplit(reference)
            if parsed.scheme in {"http", "https", "mailto"}:
                continue
            if parsed.path:
                target = (document.parent / parsed.path).resolve()
                self.assertTrue(target.is_file(), f"missing local reference: {reference}")
            if parsed.fragment:
                self.assertIn(parsed.fragment, ids, f"missing fragment target: {reference}")

    def test_license_is_gpl_version_3(self):
        license_text = (ROOT / "LICENSE").read_text()
        self.assertIn("GNU GENERAL PUBLIC LICENSE", license_text)
        self.assertIn("Version 3, 29 June 2007", license_text)


if __name__ == "__main__":
    unittest.main()
